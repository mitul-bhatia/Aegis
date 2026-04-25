# Phase 6 — Intelligence & RAG Overhaul

> **Depends on:** Phase 4 complete (infrastructure)
>
> **Estimated effort:** 3-4 days
>
> **Goal:** Replace placeholder intelligence modules with real implementations. Upgrade RAG to use code-aware embeddings and hierarchical chunking. Add SARIF export.

---

## Task 6.1: Replace Placeholder Threat Engine

**Files:** `intelligence/threat_engine.py`

**Current problem:** Every method returns hardcoded values (`"MEDIUM"`, `0`, `[]`). The entire module is a shell.

**Steps:**
- [ ] Implement `get_repo_threats()` using real scan data:
  ```python
  async def get_repo_threats(self, repo_name: str) -> ThreatIntelligence:
      db = SessionLocal()
      try:
          repo = db.query(Repo).filter(Repo.full_name == repo_name).first()
          if not repo:
              return ThreatIntelligence(level="LOW", critical_threats=0, high_threats=0, medium_threats=0)
          
          # Count unresolved vulnerabilities by severity
          from sqlalchemy import func
          thirty_days = datetime.now(timezone.utc) - timedelta(days=30)
          counts = db.query(Scan.severity, func.count()).filter(
              Scan.repo_id == repo.id,
              Scan.created_at >= thirty_days,
              Scan.severity.isnot(None),
              Scan.status.in_([ScanStatus.EXPLOIT_CONFIRMED.value, ScanStatus.PATCHING.value, ScanStatus.FAILED.value])
          ).group_by(Scan.severity).all()
          
          severity_map = dict(counts)
          critical = severity_map.get("CRITICAL", 0)
          high = severity_map.get("HIGH", 0)
          medium = severity_map.get("MEDIUM", 0)
          
          # Calculate threat level
          if critical > 0:
              level = "CRITICAL"
          elif high >= 3:
              level = "HIGH"
          elif high > 0 or medium >= 5:
              level = "MEDIUM"
          else:
              level = "LOW"
          
          return ThreatIntelligence(level=level, critical_threats=critical, high_threats=high, medium_threats=medium)
      finally:
          db.close()
  ```

- [ ] Implement `get_global_threat_level()` by aggregating across all repos
- [ ] Implement `get_emergency_repos()` — repos with CRITICAL unresolved vulns

**Verification:**
- Repos with exploit-confirmed CRITICALs show as `CRITICAL` threat level
- Clean repos show as `LOW`
- Global level reflects worst-case across all repos

---

## Task 6.2: Replace Placeholder ML Predictor

**Files:** `ml/vulnerability_predictor.py`

**Current problem:** Risk prediction is based on repo name string matching. `accuracy = 0.87` is a lie.

**Steps:**
- [ ] Implement actual prediction using scan history features:
  ```python
  async def predict_repo_risk(self, repo: Repo) -> float:
      db = SessionLocal()
      try:
          # Feature engineering from historical data
          total_scans = db.query(Scan).filter(Scan.repo_id == repo.id).count()
          vuln_scans = db.query(Scan).filter(
              Scan.repo_id == repo.id,
              Scan.vulnerability_type.isnot(None)
          ).count()
          fixed_scans = db.query(Scan).filter(
              Scan.repo_id == repo.id,
              Scan.status == ScanStatus.FIXED.value
          ).count()
          
          if total_scans == 0:
              return 0.5  # Unknown risk
          
          # Vulnerability rate
          vuln_rate = vuln_scans / total_scans
          
          # Fix lag (avg time to fix)
          # More data = better prediction
          
          # Weighted score
          risk = min(vuln_rate * 1.5 + (1 - (fixed_scans / max(vuln_scans, 1))) * 0.3, 1.0)
          return round(risk, 2)
      finally:
          db.close()
  ```

- [ ] Track prediction accuracy by comparing predictions against actual scan results
- [ ] Remove fake accuracy metrics

**Verification:**
- Repos with high vuln rates get higher risk scores
- New repos (no scans) default to 0.5
- Risk factors are based on actual data, not string matching

---

## Task 6.3: Upgrade RAG with Code-Aware Chunking

**Files:** `rag/indexer.py`, `rag/retriever.py`

**Current problem:** Files are indexed as one giant chunk (first 1000 chars). No function-level granularity.

**Steps:**
- [ ] Implement function-level chunking for Python files:
  ```python
  def chunk_python_file(content: str, file_path: str) -> list[dict]:
      """Split a Python file into function/class-level chunks."""
      import ast
      chunks = []
      try:
          tree = ast.parse(content)
          for node in ast.walk(tree):
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                  start_line = node.lineno - 1
                  end_line = node.end_lineno
                  chunk_content = "\n".join(content.splitlines()[start_line:end_line])
                  chunks.append({
                      "id": f"{file_path}::{node.name}",
                      "content": chunk_content,
                      "type": "class" if isinstance(node, ast.ClassDef) else "function",
                      "name": node.name,
                      "start_line": start_line + 1,
                      "end_line": end_line,
                      "file": file_path
                  })
      except SyntaxError:
          # Fallback: chunk by fixed size
          pass
      
      # Always include full file as a chunk too (for file-level queries)
      chunks.append({
          "id": file_path,
          "content": content[:2000],
          "type": "file",
          "name": file_path,
          "start_line": 1,
          "end_line": content.count("\n") + 1,
          "file": file_path
      })
      return chunks
  ```

- [ ] Update `index_repository()` to use function-level chunks:
  ```python
  # Instead of indexing one doc per file:
  chunks = chunk_python_file(content, relative_path)
  for chunk in chunks:
      batch_ids.append(chunk["id"])
      batch_docs.append(chunk["content"])
      batch_metas.append({
          "file_path": chunk["file"],
          "chunk_type": chunk["type"],
          "name": chunk["name"],
          "start_line": chunk["start_line"],
          "end_line": chunk["end_line"],
      })
  ```

- [ ] Add JS/TS chunking using regex (class/function detection)
- [ ] Update retriever to return function-level context with line numbers

**Verification:**
- After indexing, ChromaDB has multiple chunks per file
- Querying "SQL injection in get_user" returns the specific `get_user()` function, not a random 1000-char slice

---

## Task 6.4: Upgrade Embedding Model

**Files:** `rag/indexer.py`, `config.py`

**Steps:**
- [ ] Replace ChromaDB's `DefaultEmbeddingFunction` with a code-aware model:
  ```python
  # Option A: Use Sentence Transformers (offline, no API key)
  from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
  _embedding_fn = SentenceTransformerEmbeddingFunction(
      model_name="BAAI/bge-small-en-v1.5"  # or "nomic-ai/nomic-embed-text-v1.5"
  )
  
  # Option B: Use an API (Voyage/Jina) for even better code embeddings
  # Requires API key but produces much better semantic similarity for code
  ```

- [ ] The default `all-MiniLM-L6-v2` works but isn't optimized for code
- [ ] `BAAI/bge-small-en-v1.5` is small, fast, and much better for technical content

**Verification:**
- Re-index a repo → embedding model download happens once
- Retrieval returns more relevant results for security queries

---

## Task 6.5: Add SARIF Export

**Files:** NEW `utils/sarif.py`, NEW route `routes/export.py`

**Steps:**
- [ ] Create SARIF generator:
  ```python
  def generate_sarif_report(scan: Scan, findings: list[dict]) -> dict:
      """Generate a SARIF 2.1.0 JSON report from scan findings."""
      return {
          "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
          "version": "2.1.0",
          "runs": [{
              "tool": {
                  "driver": {
                      "name": "Aegis Security",
                      "version": "2.0.0",
                      "informationUri": "https://github.com/Jivit87/Aegis"
                  }
              },
              "results": [
                  {
                      "ruleId": f.get("vuln_type", "unknown"),
                      "level": _severity_to_sarif(f.get("severity")),
                      "message": {"text": f.get("description", "")},
                      "locations": [{
                          "physicalLocation": {
                              "artifactLocation": {"uri": f.get("file", "")},
                              "region": {"startLine": f.get("line_start", 1)}
                          }
                      }]
                  }
                  for f in findings
              ]
          }]
      }
  ```
- [ ] Add export endpoint:
  ```python
  @router.get("/api/v1/scans/{scan_id}/sarif")
  async def export_sarif(scan_id: int):
      ...
  ```
- [ ] Add download button in frontend scan detail page

**Verification:**
- Download SARIF file from a completed scan
- Upload to GitHub Code Scanning → results appear in Security tab

---

## Task 6.6: Add Vulnerability Pattern Library

**Files:** NEW `intelligence/vuln_patterns.py`

**Steps:**
- [ ] Create a local pattern library that learns from successful findings:
  ```python
  VULN_PATTERNS = {
      "sql_injection": {
          "indicators": ["cursor.execute(f\"", "format(", "% (", ".format("],
          "safe_patterns": ["cursor.execute(\"...\", (param,))", "parameterized"],
          "cve_examples": ["CVE-2019-12922", "CVE-2020-13254"],
          "fix_templates": ["Use parameterized queries"]
      },
      "xss": {
          "indicators": ["innerHTML", "document.write", "render_template_string"],
          ...
      },
      ...
  }
  ```
- [ ] Feed patterns to the Finder agent as additional context
- [ ] After each successful fix, extract the pattern and update the library

**Verification:**
- Finder receives vulnerability pattern context
- Pattern library grows after each successful remediation

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 6.1 | Replace placeholder threat engine | 🔴 Critical | `intelligence/threat_engine.py` |
| 6.2 | Replace placeholder ML predictor | 🔴 Critical | `ml/vulnerability_predictor.py` |
| 6.3 | Code-aware RAG chunking | 🟠 High | `rag/indexer.py`, `rag/retriever.py` |
| 6.4 | Upgrade embedding model | 🟡 Medium | `rag/indexer.py`, `config.py` |
| 6.5 | SARIF export | 🟡 Medium | NEW `utils/sarif.py`, NEW `routes/export.py` |
| 6.6 | Vulnerability pattern library | 🟡 Medium | NEW `intelligence/vuln_patterns.py` |

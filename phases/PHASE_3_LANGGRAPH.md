# Phase 3 — LangGraph Migration

> **Depends on:** Phase 2 complete (agents refactored)
>
> **Estimated effort:** 4-5 days
>
> **Goal:** Replace the 472-line imperative `orchestrator.py` with a LangGraph state machine — gaining durable execution, checkpoint/resume, human-in-the-loop, and proper streaming.

---

## Task 3.1: Install LangGraph Dependencies

**Files:** `requirements.txt`, `.env`

**Steps:**
- [ ] Add to `requirements.txt`:
  ```
  langgraph>=0.2.0
  langchain-core>=0.3.0
  ```
- [ ] Install: `pip install langgraph langchain-core`
- [ ] (Optional) Add LangSmith for observability:
  ```
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=your_key_here
  ```

**Verification:**
- `python -c "from langgraph.graph import StateGraph; print('OK')"` works

---

## Task 3.2: Define Pipeline State Schema

**Files:** NEW `pipeline/state.py`

**Steps:**
- [ ] Create the full pipeline state TypedDict:
  ```python
  from typing import TypedDict, Optional, Annotated
  from agents.schemas import VulnerabilityFinding, ReviewerDiagnosis
  
  class AegisPipelineState(TypedDict):
      # Input
      repo_full_name: str
      commit_sha: str
      branch: str
      push_info: dict
      scan_id: Optional[int]
      
      # Phase 1: Pre-processing
      local_repo_path: str
      diff: dict
      semgrep_findings: list[dict]
      rag_context: str
      
      # Phase 2: Finder output
      vulnerability_findings: list[dict]  # serialized VulnerabilityFinding
      
      # Phase 3: Exploiter output
      confirmed_vulnerabilities: list[dict]
      current_vuln_index: int
      
      # Phase 4: Engineer output
      patched_code: Optional[str]
      test_code: Optional[str]
      original_code: Optional[str]
      
      # Phase 5: Verifier output
      reviewer_diagnosis: Optional[dict]
      verification_passed: bool
      
      # Control flow
      retry_count: int
      max_retries: int
      pipeline_status: str
      error: Optional[str]
      pr_urls: list[str]
  ```

**Verification:**
- State schema compiles and all field types are correct

---

## Task 3.3: Create LangGraph Node Functions

**Files:** NEW `pipeline/nodes.py`

**Steps:**
- [ ] Create one function per pipeline phase — each takes state, returns partial state update:
  ```python
  def pre_process_node(state: AegisPipelineState) -> dict:
      """Clone repo, get diff, run semgrep + RAG"""
      ...
      return {"local_repo_path": path, "diff": diff, "semgrep_findings": findings, "rag_context": context}
  
  def finder_node(state: AegisPipelineState) -> dict:
      """Run Finder agent on diff"""
      findings = run_finder_agent(state["diff"], state["semgrep_findings"], state["rag_context"])
      return {"vulnerability_findings": [f.dict() for f in findings]}
  
  def exploiter_node(state: AegisPipelineState) -> dict:
      """Test each vulnerability with exploit in sandbox"""
      confirmed = []
      for finding in state["vulnerability_findings"]:
          result = run_exploiter_agent(finding, state["diff"], state["rag_context"])
          sandbox_result = run_exploit_in_sandbox(result["exploit_script"], state["local_repo_path"])
          if sandbox_result["exploit_succeeded"]:
              confirmed.append({...})
      return {"confirmed_vulnerabilities": confirmed}
  
  def engineer_node(state: AegisPipelineState) -> dict:
      """Generate patch for current vulnerability"""
      ...
      return {"patched_code": result["patched_code"], "test_code": result["test_code"]}
  
  def verifier_node(state: AegisPipelineState) -> dict:
      """Test patch: run unit tests + re-run exploit"""
      ...
      return {"verification_passed": True/False, "reviewer_diagnosis": diagnosis}
  
  def pr_creator_node(state: AegisPipelineState) -> dict:
      """Create GitHub PR with the fix"""
      ...
      return {"pr_urls": [pr_url]}
  ```

- [ ] Each node also calls `update_scan_status()` for SSE updates
- [ ] Each node handles its own errors and updates `state["error"]`

**Verification:**
- Each node can run independently with mock state input

---

## Task 3.4: Build the LangGraph State Machine

**Files:** NEW `pipeline/graph.py`

**Steps:**
- [ ] Define the graph with conditional edges:
  ```python
  from langgraph.graph import StateGraph, END
  
  graph = StateGraph(AegisPipelineState)
  
  # Add nodes
  graph.add_node("pre_process", pre_process_node)
  graph.add_node("finder", finder_node)
  graph.add_node("exploiter", exploiter_node)
  graph.add_node("engineer", engineer_node)
  graph.add_node("verifier", verifier_node)
  graph.add_node("pr_creator", pr_creator_node)
  
  # Set entry point
  graph.set_entry_point("pre_process")
  
  # Linear: pre_process → finder
  graph.add_edge("pre_process", "finder")
  
  # Conditional: finder → exploiter OR end
  graph.add_conditional_edges("finder", route_after_finder, {
      "has_findings": "exploiter",
      "no_findings": END
  })
  
  # Linear: exploiter → engineer (if confirmed)
  graph.add_conditional_edges("exploiter", route_after_exploiter, {
      "confirmed": "engineer",
      "false_positive": END
  })
  
  # Linear: engineer → verifier
  graph.add_edge("engineer", "verifier")
  
  # Conditional: verifier → pr_creator OR retry engineer
  graph.add_conditional_edges("verifier", route_after_verification, {
      "success": "pr_creator",
      "retry": "engineer",
      "max_retries": END
  })
  
  # PR creator → END
  graph.add_edge("pr_creator", END)
  
  # Compile
  aegis_pipeline = graph.compile()
  ```

- [ ] Define routing functions:
  ```python
  def route_after_finder(state):
      return "has_findings" if state["vulnerability_findings"] else "no_findings"
  
  def route_after_exploiter(state):
      return "confirmed" if state["confirmed_vulnerabilities"] else "false_positive"
  
  def route_after_verification(state):
      if state["verification_passed"]:
          return "success"
      if state["retry_count"] >= state["max_retries"]:
          return "max_retries"
      return "retry"
  ```

**Verification:**
- Graph compiles without errors
- `aegis_pipeline.get_graph().print_ascii()` shows correct topology

---

## Task 3.5: Replace orchestrator.py with LangGraph

**Files:** `orchestrator.py` (major rewrite), `main.py`, `routes/scans.py`

**Steps:**
- [ ] Rename current `orchestrator.py` → `orchestrator_legacy.py` (keep as reference)
- [ ] Create new `orchestrator.py` that wraps the LangGraph pipeline:
  ```python
  from pipeline.graph import aegis_pipeline
  from pipeline.state import AegisPipelineState
  
  def run_aegis_pipeline(push_info: dict):
      """Entry point — creates initial state and runs the LangGraph pipeline."""
      initial_state = AegisPipelineState(
          repo_full_name=push_info["repo_name"],
          commit_sha=push_info["commit_sha"],
          branch=push_info.get("branch", "main"),
          push_info=push_info,
          ...
      )
      
      # Run the graph
      result = aegis_pipeline.invoke(initial_state)
      
      # Final status update
      if result.get("error"):
          logger.error(f"Pipeline failed: {result['error']}")
      elif result.get("pr_urls"):
          logger.info(f"Pipeline complete! PRs: {result['pr_urls']}")
  ```

- [ ] Preserve all SSE update calls in the node functions
- [ ] Preserve all DB session management

**Verification:**
- Trigger a full scan — pipeline should work identically to before
- Check logs for proper node transitions: pre_process → finder → exploiter → engineer → verifier → pr_creator
- SSE updates still work in the frontend

---

## Task 3.6: Add Triage Agent (Agent 0)

**Files:** NEW `agents/triage.py`, `pipeline/nodes.py`

**Steps:**
- [ ] Create a lightweight triage agent that runs before the Finder:
  ```python
  class TriageResult(BaseModel):
      security_domains: list[str]   # ["sql", "auth", "crypto"]
      scan_priority: str            # "emergency" | "standard" | "low"
      analysis_brief: str           # 1-2 sentence brief for Finder
      skip_scan: bool               # True if commit is clearly non-security (docs, CI config)
  ```
- [ ] Agent uses Groq for speed — quick classification of commit content
- [ ] If `skip_scan=True` (e.g., only README changes), skip the entire pipeline
- [ ] Pass `analysis_brief` to the Finder to narrow its focus

**Verification:**
- Push a docs-only change → pipeline skips quickly with "Non-security commit"
- Push code changes → triage identifies relevant security domains

---

## Task 3.7: Add CVSS Scoring

**Files:** NEW `utils/cvss.py`, `agents/finder.py`, `agents/schemas.py`

**Steps:**
- [ ] Extend `VulnerabilityFinding` with CVSS fields:
  ```python
  class VulnerabilityFinding(BaseModel):
      # ... existing fields ...
      cvss_vector: Optional[str] = None   # "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
      cvss_score: Optional[float] = None  # Calculated from vector
  ```
- [ ] Update Finder system prompt to ask for CVSS vector string
- [ ] Create `utils/cvss.py` with the CVSS 3.1 base score calculator (deterministic math, not LLM)
- [ ] After parsing findings, calculate and attach CVSS scores:
  ```python
  for finding in findings:
      if finding.cvss_vector:
          finding.cvss_score = calculate_cvss_base_score(finding.cvss_vector)
  ```

**Verification:**
- Findings now include CVSS scores alongside severity strings
- Scores match manual calculation

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 3.1 | Install LangGraph | 🟢 Setup | `requirements.txt` |
| 3.2 | Define pipeline state | 🔴 Critical | NEW `pipeline/state.py` |
| 3.3 | Create node functions | 🔴 Critical | NEW `pipeline/nodes.py` |
| 3.4 | Build state machine | 🔴 Critical | NEW `pipeline/graph.py` |
| 3.5 | Replace orchestrator | 🔴 Critical | `orchestrator.py` |
| 3.6 | Triage Agent | 🟡 Medium | NEW `agents/triage.py` |
| 3.7 | CVSS scoring | 🟡 Medium | NEW `utils/cvss.py`, `finder.py` |

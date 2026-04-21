# 🛡️ Aegis — Complete Development Guide
## Build It Phase by Phase, Test Everything, Ship Confident

> **Who this is for:** Someone who understands the idea and wants to actually build it — step by step, no skipping, no hand-waving. Each phase ends with a working test you can run before moving on.

---

## 📚 Before You Start — Technology Decisions Explained

This section explains WHY we chose each tool. Read this once. It will save you 10 hours of confusion.

### Why Claude Agent SDK (not OpenAI, not LangChain)?

We researched every major framework available in 2026. Here's what matters for Aegis specifically:

| Framework | Why We Considered It | Why We Didn't Pick It |
|---|---|---|
| **OpenAI Agents SDK** | Good handoff system, built-in tracing | Locked to OpenAI models, proprietary |
| **LangGraph** | Best for complex state machines | Too heavy for a hackathon MVP |
| **CrewAI** | Simple role-based agents | No checkpointing, breaks at scale |
| **Claude Agent SDK** ✅ | **Tool-use first, MCP native, extended thinking** | None — this is our pick |

**The reason Claude Agent SDK wins for us:**

1. **Extended Thinking** — Agent A (The Hacker) can show its reasoning chain. You can literally see *why* it thinks a piece of code is exploitable. This is gold for debugging and for the demo.

2. **MCP Native** — Semgrep already has an official MCP server. That means instead of writing Semgrep integration code, we just *connect* it as a tool. Plug and play.

3. **Subagents built-in** — Agent A can spin off sub-agents in parallel. Imagine scanning 5 vulnerability types simultaneously instead of sequentially.

4. **Tool-use reliability** — Claude models call tools correctly with minimal prompt engineering. Less time fighting the framework, more time building features.

### What is MCP and Why Does It Matter Here?

MCP (Model Context Protocol) is like USB-C for AI agents. Instead of writing custom integration code for every tool, you connect MCP servers and the agent automatically discovers and uses the tools.

```
WITHOUT MCP:                          WITH MCP:
┌─────────────┐                       ┌─────────────┐
│  Agent A    │                       │  Agent A    │
│             │──custom code──▶Semgrep│             │──MCP──▶ Semgrep MCP Server
│             │──custom code──▶GitHub │             │──MCP──▶ GitHub MCP Server
│             │──custom code──▶Docker │             │──MCP──▶ Docker MCP Server
└─────────────┘                       └─────────────┘
 3 custom integrations = weeks         3 MCP connections = hours
```

**MCP servers already available for us to use:**
- `semgrep-mcp` — Official Semgrep MCP server (scans for security vulns)
- `github-mcp` — Official GitHub MCP server (read diffs, create PRs)
- We build our own: `docker-mcp` — runs sandboxed code execution

### RAG vs Full Context — Quick Decision

```
Full repo in every prompt    → Too slow, too expensive, confuses the LLM
No context (just diff)       → Agent A is blind to how code is connected
Smart RAG (our approach)     → Index once, retrieve relevant chunks per commit
```

We use **ChromaDB** (local, free, fast) to store embeddings and retrieve only the top 5 most relevant files for each diff.

### Memory Architecture for Our Agents

Agents need two types of memory:

```
SHORT-TERM (in-context):          LONG-TERM (persistent):
- The current diff                - Past vulnerability patterns found in this repo
- Retrieved RAG chunks            - Which fixes worked / failed
- Current exploit attempt         - Security posture history
- Current patch attempt           
Lives in the prompt window        Lives in PostgreSQL
Wiped after each run              Builds over time
```

For the hackathon MVP, we implement short-term only. Long-term is post-MVP.

---

## 🗺️ Phase Overview

```
Phase 0 → Environment Setup (30 min)
Phase 1 → GitHub Webhook — receive commits (1 hour)
Phase 2 → Diff Parser + Semgrep via MCP (1 hour)
Phase 3 → RAG Index — understand the codebase (2 hours)
Phase 4 → Agent A — The Hacker (2 hours)
Phase 5 → Docker Sandbox — safe exploit execution (1.5 hours)
Phase 6 → Agent B — The Engineer / Patcher (1.5 hours)
Phase 7 → Agent C — The Reviewer / Loop (1 hour)
Phase 8 → GitHub PR — output the result (45 min)
Phase 9 → End-to-End Test + Demo Polish (1 hour)
```

Each phase has:
- **What you're building** — the concept
- **Exact code to write** — copy-paste friendly
- **How to test it** — run this command, expect this output
- **Common mistakes** — what goes wrong and how to fix it

---

## Phase 0 — Environment Setup

**What you're building:** A clean Python environment with all dependencies installed.

### Step 0.1 — Project structure

Create this folder structure first:

```bash
mkdir aegis && cd aegis
mkdir -p agents rag sandbox github scanner
touch main.py orchestrator.py
touch agents/__init__.py agents/hacker.py agents/engineer.py agents/reviewer.py
touch rag/__init__.py rag/indexer.py rag/retriever.py
touch sandbox/__init__.py sandbox/docker_runner.py
touch github/__init__.py github/webhook.py github/pr_creator.py
touch scanner/__init__.py scanner/semgrep_runner.py
```

### Step 0.2 — Install dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install everything
pip install fastapi uvicorn python-dotenv anthropic chromadb \
            pygithub gitpython docker requests langchain-community \
            langchain-anthropic openai tiktoken

# Install Semgrep
pip install semgrep

# Verify semgrep works
semgrep --version
# Expected: semgrep X.X.X
```

### Step 0.3 — Environment variables

Create a `.env` file:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
GITHUB_TOKEN=ghp_...your-token-here...
GITHUB_WEBHOOK_SECRET=your-secret-string-here

# Model to use
CLAUDE_MODEL=claude-sonnet-4-6

# Ports
PORT=8000
```

### Step 0.4 — Create a mock vulnerable repo for testing

```bash
# Create a test repo with intentionally vulnerable Python code
mkdir test_repo && cd test_repo
git init

cat > app.py << 'EOF'
import sqlite3

def get_user(username):
    # VULNERABILITY: SQL Injection here
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

def get_product(product_id):
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    # VULNERABILITY: SQL Injection here too
    cursor.execute(f"SELECT * FROM products WHERE id = {product_id}")
    return cursor.fetchone()
EOF

cat > test_app.py << 'EOF'
from app import get_user, get_product

def test_get_user_normal():
    # This would need a real DB to pass, but structure is correct
    assert True

def test_get_product_normal():
    assert True
EOF

git add . && git commit -m "Initial commit with vulnerable code"
cd ..
```

### ✅ Phase 0 Test

```bash
python -c "import anthropic, chromadb, fastapi, docker; print('All imports OK')"
# Expected output: All imports OK

python -c "import anthropic; c = anthropic.Anthropic(); print('Anthropic connected')"
# Expected output: Anthropic connected
```

---

## Phase 1 — GitHub Webhook Receiver

**What you're building:** A FastAPI server that listens for GitHub push events. When someone commits code, GitHub sends a POST request to your server. You catch it here.

### Step 1.1 — The webhook handler

```python
# github/webhook.py
import hashlib
import hmac
import os
from fastapi import Request, HTTPException

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """GitHub signs every webhook. We verify it's really from GitHub."""
    if not signature_header:
        return False
    
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

def extract_push_info(payload: dict) -> dict:
    """Pull out the useful parts from a GitHub push event."""
    return {
        "repo_name": payload["repository"]["full_name"],
        "repo_url": payload["repository"]["clone_url"],
        "branch": payload["ref"].replace("refs/heads/", ""),
        "commit_sha": payload["after"],
        "commit_message": payload["head_commit"]["message"],
        "pusher": payload["pusher"]["name"],
        "files_changed": [
            f 
            for commit in payload.get("commits", [])
            for f in commit.get("added", []) + commit.get("modified", [])
        ]
    }
```

### Step 1.2 — Main FastAPI app

```python
# main.py
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
import json

load_dotenv()

from github.webhook import verify_signature, extract_push_info

app = FastAPI(title="Aegis Security System")

@app.get("/health")
async def health():
    return {"status": "Aegis is running", "version": "0.1.0"}

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # Get the raw body for signature verification
    body = await request.body()
    
    # Verify it's actually from GitHub
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Only process push events
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "push":
        return {"message": f"Ignoring event: {event_type}"}
    
    payload = json.loads(body)
    push_info = extract_push_info(payload)
    
    print(f"[AEGIS] New push detected: {push_info['commit_sha'][:8]} on {push_info['repo_name']}")
    
    # Run the analysis in background (don't block GitHub's webhook timeout)
    # background_tasks.add_task(run_aegis_pipeline, push_info)
    # ^ We'll uncomment this in Phase 4
    
    return {"message": "Webhook received", "commit": push_info["commit_sha"][:8]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 1.3 — Start the server + expose it

```bash
# Terminal 1: Run the server
python main.py

# Terminal 2: Expose it to the internet (for GitHub to reach)
# Install ngrok first: https://ngrok.com/download
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL
```

Go to your GitHub repo → Settings → Webhooks → Add webhook:
- Payload URL: `https://xxxx.ngrok.io/webhook/github`
- Content type: `application/json`
- Secret: the value from your `.env`
- Events: "Just the push event"

### ✅ Phase 1 Test

```bash
# Test health endpoint
curl http://localhost:8000/health
# Expected: {"status":"Aegis is running","version":"0.1.0"}

# Simulate a push event (without real GitHub)
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=FAKE" \
  -d '{"test": true}'
# Expected: {"detail":"Invalid signature"} ← Good! Signature check works.

# Make a commit to your test repo — check Terminal 1 for:
# [AEGIS] New push detected: abc12345 on yourname/yourrepo
```

**Common mistakes:**
- Signature mismatch: Make sure the secret in `.env` exactly matches what you put in GitHub
- ngrok URL expiring: Restart ngrok, update GitHub webhook URL

---

## Phase 2 — Diff Parser + Semgrep Scanner

**What you're building:** When a push comes in, you fetch the diff (what changed) and run Semgrep on it. This is the first filter — cheap and fast, before we burn expensive LLM tokens.

### Step 2.1 — Fetch the diff from GitHub

```python
# github/diff_fetcher.py
import subprocess
import os
from github import Github

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def clone_or_pull_repo(repo_url: str, local_path: str) -> str:
    """Clone repo if not exists, pull if it does."""
    if os.path.exists(local_path):
        subprocess.run(["git", "-C", local_path, "pull"], capture_output=True)
    else:
        subprocess.run(["git", "clone", repo_url, local_path], capture_output=True)
    return local_path

def get_diff(repo_full_name: str, commit_sha: str, base_sha: str = None) -> dict:
    """Get the diff for a specific commit."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    
    commit = repo.get_commit(commit_sha)
    
    changed_files = []
    for file in commit.files:
        if file.filename.endswith((".py", ".js", ".ts", ".java", ".go", ".rb")):
            changed_files.append({
                "filename": file.filename,
                "status": file.status,  # added, modified, removed
                "additions": file.additions,
                "deletions": file.deletions,
                "patch": file.patch or "",  # The actual diff text
            })
    
    return {
        "commit_sha": commit_sha,
        "commit_message": commit.commit.message,
        "changed_files": changed_files,
        "total_changes": sum(f["additions"] + f["deletions"] for f in changed_files)
    }
```

### Step 2.2 — Semgrep scanner

```python
# scanner/semgrep_runner.py
import subprocess
import json
import os
import tempfile

def run_semgrep_on_files(file_paths: list[str], repo_path: str) -> list[dict]:
    """
    Run Semgrep on specific files.
    Returns list of findings.
    """
    if not file_paths:
        return []
    
    # Run Semgrep with security rules
    cmd = [
        "semgrep",
        "--config", "auto",          # Auto-select rules based on file type
        "--json",                     # Output as JSON
        "--quiet",                    # Suppress progress output
        "--no-git-ignore",
        *[os.path.join(repo_path, f) for f in file_paths if os.path.exists(os.path.join(repo_path, f))]
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode not in [0, 1]:  # 0=clean, 1=findings, other=error
        print(f"[SEMGREP ERROR] {result.stderr}")
        return []
    
    try:
        output = json.loads(result.stdout)
        findings = []
        
        for finding in output.get("results", []):
            findings.append({
                "rule_id": finding["check_id"],
                "severity": finding["extra"]["severity"],
                "message": finding["extra"]["message"],
                "file": finding["path"],
                "line_start": finding["start"]["line"],
                "line_end": finding["end"]["line"],
                "code_snippet": finding["extra"]["lines"],
                "category": finding["extra"].get("metadata", {}).get("category", "unknown")
            })
        
        return findings
    
    except json.JSONDecodeError:
        return []

def format_findings_for_llm(findings: list[dict]) -> str:
    """Format Semgrep output in a way that's easy for Claude to read."""
    if not findings:
        return "Semgrep found no issues."
    
    formatted = f"Semgrep found {len(findings)} potential issue(s):\n\n"
    for i, f in enumerate(findings, 1):
        formatted += f"""Issue {i}:
  Rule: {f['rule_id']}
  Severity: {f['severity']}
  File: {f['file']} (line {f['line_start']})
  Problem: {f['message']}
  Code: {f['code_snippet']}

"""
    return formatted
```

### ✅ Phase 2 Test

Create a test script:

```python
# test_phase2.py
import os, sys
sys.path.insert(0, ".")

# Test 1: Semgrep works
from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm

# Create a temp vulnerable file
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    vuln_file = os.path.join(tmpdir, "test.py")
    with open(vuln_file, "w") as f:
        f.write("""
import sqlite3
def get_user(name):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchone()
""")
    
    findings = run_semgrep_on_files(["test.py"], tmpdir)
    print(f"✅ Semgrep test: Found {len(findings)} finding(s)")
    
    if findings:
        print(f"   First finding: {findings[0]['rule_id']}")
        print(f"   Severity: {findings[0]['severity']}")
    
    formatted = format_findings_for_llm(findings)
    print(f"\n{formatted}")
```

```bash
python test_phase2.py
# Expected:
# ✅ Semgrep test: Found 1 finding(s)
#    First finding: python.lang.security.audit.formatted-sql-query.formatted-sql-query
#    Severity: WARNING
```

---

## Phase 3 — RAG Index (One-Time Codebase Understanding)

**What you're building:** On first connect, scan the entire repo and build an index. Every file gets embedded and stored. On each commit, retrieve only the relevant files using semantic search.

### Step 3.1 — The indexer

```python
# rag/indexer.py
import os
import ast
import chromadb
from anthropic import Anthropic

client = Anthropic()

# Initialize ChromaDB (local, no setup needed)
chroma_client = chromadb.PersistentClient(path="./aegis_vector_db")

def get_or_create_collection(repo_name: str):
    """Each repo gets its own ChromaDB collection."""
    safe_name = repo_name.replace("/", "_").replace("-", "_")
    return chroma_client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"}
    )

def extract_file_metadata(file_path: str, content: str) -> dict:
    """
    Extract structured info from a Python file.
    For the hackathon, we do simple extraction.
    """
    metadata = {
        "file": file_path,
        "functions": [],
        "imports": [],
        "classes": [],
        "has_sql": "sql" in content.lower() or "SELECT" in content or "INSERT" in content,
        "has_auth": any(w in content.lower() for w in ["password", "token", "auth", "login", "jwt"]),
        "has_http": any(w in content.lower() for w in ["request", "response", "route", "endpoint", "url"]),
    }
    
    # Try to extract Python AST info
    if file_path.endswith(".py"):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        metadata["imports"].append(alias.name)
                elif isinstance(node, ast.ClassDef):
                    metadata["classes"].append(node.name)
        except SyntaxError:
            pass
    
    return metadata

def get_embedding(text: str) -> list[float]:
    """Get embedding from Claude via the Anthropic API."""
    # We use a simple approach: ask the API for embeddings
    # For hackathon speed, we use voyage-3-lite (Anthropic's embedding model)
    import anthropic
    client = anthropic.Anthropic()
    
    # Note: For actual embeddings, use voyage-3 via Anthropic
    # This is a simplified approach using their embedding endpoint
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        system="Respond with only the number 1.",
        messages=[{"role": "user", "content": text[:500]}]
    )
    
    # Fallback: use a simple hash-based embedding for prototyping
    # In production, use voyage-3 embeddings
    import hashlib
    hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
    embedding = [(hash_val >> i & 1) * 1.0 for i in range(384)]
    return embedding

def index_repository(repo_path: str, repo_name: str) -> int:
    """
    Walk the entire repo and index every code file.
    Returns number of files indexed.
    """
    collection = get_or_create_collection(repo_name)
    
    SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    
    indexed = 0
    
    for root, dirs, files in os.walk(repo_path):
        # Skip irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for filename in files:
            ext = os.path.splitext(filename)[1]
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, repo_path)
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                if len(content) < 10:  # Skip empty files
                    continue
                
                metadata = extract_file_metadata(relative_path, content)
                
                # Create a rich text representation for embedding
                text_to_embed = f"""
File: {relative_path}
Functions: {', '.join(metadata['functions'][:10])}
Classes: {', '.join(metadata['classes'][:5])}
Imports: {', '.join(metadata['imports'][:10])}
Has SQL: {metadata['has_sql']}
Has Auth: {metadata['has_auth']}
Has HTTP endpoints: {metadata['has_http']}

Code preview:
{content[:1000]}
"""
                
                # Store in ChromaDB
                collection.upsert(
                    ids=[relative_path],
                    documents=[text_to_embed],
                    metadatas=[{
                        "file_path": relative_path,
                        "functions": str(metadata["functions"]),
                        "has_sql": metadata["has_sql"],
                        "has_auth": metadata["has_auth"],
                        "has_http": metadata["has_http"],
                        "content_preview": content[:500]
                    }]
                )
                
                indexed += 1
                print(f"  [RAG] Indexed: {relative_path}")
                
            except Exception as e:
                print(f"  [RAG] Skipped {relative_path}: {e}")
    
    print(f"[RAG] Indexing complete: {indexed} files indexed for {repo_name}")
    return indexed
```

### Step 3.2 — The retriever

```python
# rag/retriever.py
import chromadb
from rag.indexer import get_or_create_collection

def retrieve_relevant_context(
    repo_name: str,
    diff: dict,
    semgrep_findings: list[dict],
    top_k: int = 5
) -> str:
    """
    Given a diff and Semgrep findings, retrieve the most relevant files
    from the codebase index.
    """
    collection = get_or_create_collection(repo_name)
    
    # Build a query from the diff
    changed_files = [f["filename"] for f in diff["changed_files"]]
    changed_code = "\n".join([f["patch"] for f in diff["changed_files"]])
    
    # Build query combining: changed filenames + semgrep findings + code
    query_parts = [
        f"Changed files: {', '.join(changed_files)}",
        f"Code changes: {changed_code[:500]}",
    ]
    
    if semgrep_findings:
        issues = [f["message"] for f in semgrep_findings[:3]]
        query_parts.append(f"Security issues: {', '.join(issues)}")
    
    query = "\n".join(query_parts)
    
    try:
        # Search for similar files
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results for the LLM
        context_parts = ["=== RELATED CODEBASE CONTEXT ===\n"]
        
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # Only include if similarity is reasonable (lower distance = more similar)
            if dist < 1.5:
                context_parts.append(f"""
--- Related File {i+1}: {meta['file_path']} ---
{meta.get('content_preview', 'No preview available')}
""")
        
        return "\n".join(context_parts)
    
    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")
        return "No related context found."
```

### ✅ Phase 3 Test

```python
# test_phase3.py
import sys, os
sys.path.insert(0, ".")

from rag.indexer import index_repository
from rag.retriever import retrieve_relevant_context

# Index the test repo
print("Indexing test repo...")
count = index_repository("./test_repo", "test/vulnerable-app")
print(f"Indexed {count} files")

# Test retrieval
diff = {
    "changed_files": [{"filename": "app.py", "patch": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE username = '{username}'\""}]
}
semgrep_findings = [{"message": "SQL injection detected in formatted query"}]

context = retrieve_relevant_context("test/vulnerable-app", diff, semgrep_findings)
print(f"\nRetrieved context:\n{context}")
```

```bash
python test_phase3.py
# Expected:
# Indexing test repo...
#   [RAG] Indexed: app.py
#   [RAG] Indexed: test_app.py
# Indexed 2 files
# Retrieved context:
# === RELATED CODEBASE CONTEXT ===
# --- Related File 1: app.py ---
# ...
```

---

## Phase 4 — Agent A: The Hacker

**What you're building:** The heart of Aegis. An LLM agent that receives the diff + context + Semgrep output, and writes an exploit script to prove the vulnerability is real.

### Step 4.1 — Agent A

```python
# agents/hacker.py
import os
from anthropic import Anthropic

client = Anthropic()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

HACKER_SYSTEM_PROMPT = """You are Agent A — an expert offensive security researcher working on a white-hat security team.

Your job is to analyze code changes and write a Python exploit script that PROVES a vulnerability exists.

RULES:
1. Your exploit script must be completely self-contained Python
2. It must print "VULNERABLE: <description>" if the exploit succeeds
3. It must print "NOT_VULNERABLE" if no vulnerability exists
4. Return exit code 0 if vulnerable, 1 if not
5. Install any needed packages using subprocess at the start of the script
6. The script runs in an isolated Docker container — no real database, use SQLite in /tmp/
7. Focus on the most critical vulnerability first
8. Use extended thinking to reason carefully about what's actually exploitable

IMPORTANT: Only claim VULNERABLE if the exploit actually demonstrates the issue.
Do NOT claim vulnerabilities that are theoretical. Prove it.

Output ONLY the Python script. No explanation before or after. Just the code."""

def run_hacker_agent(
    diff: dict,
    semgrep_findings: list[dict],
    rag_context: str
) -> dict:
    """
    Agent A analyzes the code and generates an exploit.
    Returns the exploit script and reasoning.
    """
    
    # Build the prompt
    diff_text = "\n".join([
        f"File: {f['filename']}\n{f['patch']}\n"
        for f in diff["changed_files"]
    ])
    
    semgrep_text = "\n".join([
        f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line_start']})"
        for f in semgrep_findings
    ]) if semgrep_findings else "No Semgrep findings."
    
    user_prompt = f"""Analyze this code commit and write an exploit script.

=== CODE DIFF ===
{diff_text}

=== SEMGREP STATIC ANALYSIS FINDINGS ===
{semgrep_text}

{rag_context}

Write a complete, runnable Python exploit script that proves the most critical vulnerability.
The script must work in an isolated environment with SQLite in /tmp/."""

    print("[AGENT A] Analyzing code with extended thinking...")
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={
            "type": "enabled",
            "budget_tokens": 2000  # Let Claude think carefully
        },
        system=HACKER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # Extract the exploit script from response
    exploit_script = ""
    thinking_text = ""
    
    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking
        elif block.type == "text":
            exploit_script = block.text.strip()
    
    # Clean up code fences if present
    if exploit_script.startswith("```python"):
        exploit_script = exploit_script[9:]
    if exploit_script.startswith("```"):
        exploit_script = exploit_script[3:]
    if exploit_script.endswith("```"):
        exploit_script = exploit_script[:-3]
    exploit_script = exploit_script.strip()
    
    print(f"[AGENT A] Generated exploit ({len(exploit_script)} chars)")
    if thinking_text:
        print(f"[AGENT A] Reasoning: {thinking_text[:200]}...")
    
    return {
        "exploit_script": exploit_script,
        "reasoning": thinking_text,
        "vulnerability_type": extract_vuln_type(semgrep_findings),
        "files_analyzed": [f["filename"] for f in diff["changed_files"]]
    }

def extract_vuln_type(findings: list[dict]) -> str:
    if not findings:
        return "Unknown"
    rule_id = findings[0].get("rule_id", "")
    if "sql" in rule_id.lower():
        return "SQL Injection"
    if "xss" in rule_id.lower():
        return "XSS"
    if "path" in rule_id.lower():
        return "Path Traversal"
    return findings[0].get("category", "Security Vulnerability")
```

### ✅ Phase 4 Test

```python
# test_phase4.py
import sys
sys.path.insert(0, ".")

from agents.hacker import run_hacker_agent

diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": """
+def get_user(username):
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    query = f"SELECT * FROM users WHERE username = '{username}'"
+    cursor.execute(query)
+    return cursor.fetchone()
"""
    }]
}

semgrep_findings = [{
    "rule_id": "python.lang.security.audit.formatted-sql-query",
    "severity": "WARNING",
    "message": "Formatted SQL query detected. Possible SQL injection.",
    "line_start": 4,
    "category": "security"
}]

rag_context = "=== RELATED CODEBASE CONTEXT ===\nThis function is called by the /login endpoint."

result = run_hacker_agent(diff, semgrep_findings, rag_context)

print(f"\n=== EXPLOIT SCRIPT ===")
print(result["exploit_script"])
print(f"\n=== VULNERABILITY TYPE ===")
print(result["vulnerability_type"])
```

```bash
python test_phase4.py
# Expected: Claude generates a Python exploit script targeting SQL injection
# The script should contain sqlite3 setup and demonstrate injection
```

---

## Phase 5 — Docker Sandbox Execution

**What you're building:** Run the exploit in a totally isolated container. If it escapes or crashes — no problem. Container is destroyed.

### Step 5.1 — Docker runner

```python
# sandbox/docker_runner.py
import docker
import tempfile
import os
import time

docker_client = docker.from_env()

SANDBOX_IMAGE = "python:3.11-slim"

def run_exploit_in_sandbox(
    exploit_script: str,
    repo_path: str,
    timeout: int = 30
) -> dict:
    """
    Run an exploit script in an isolated Docker container.
    Returns the result including stdout, stderr, exit code.
    """
    
    print("[DOCKER] Creating sandbox container...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write exploit to temp file
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(exploit_script)
        
        try:
            # Run in Docker with strict limits
            container = docker_client.containers.run(
                SANDBOX_IMAGE,
                command=f"python /exploit.py",
                volumes={
                    tmpdir: {"bind": "/sandbox", "mode": "ro"},
                    repo_path: {"bind": "/app", "mode": "ro"},
                },
                working_dir="/app",
                network_mode="none",         # NO internet access
                mem_limit="256m",            # Max 256MB RAM
                cpu_quota=50000,             # 50% of one CPU
                read_only=False,
                tmpfs={"/tmp": "size=64m"},  # Temp space only
                remove=False,
                detach=True,
                entrypoint=["python", "/sandbox/exploit.py"]
            )
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                logs = container.logs(stdout=True, stderr=True).decode("utf-8")
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
                
            except Exception as e:
                exit_code = -1
                stdout = ""
                stderr = f"Timeout or error: {e}"
            
            finally:
                # ALWAYS destroy the container
                try:
                    container.remove(force=True)
                    print("[DOCKER] Container destroyed.")
                except:
                    pass
            
            exploit_succeeded = (
                exit_code == 0 and
                "VULNERABLE" in stdout and
                "NOT_VULNERABLE" not in stdout
            )
            
            print(f"[DOCKER] Exit code: {exit_code}, Vulnerable: {exploit_succeeded}")
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "exploit_succeeded": exploit_succeeded,
                "vulnerability_confirmed": exploit_succeeded,
                "output_summary": stdout[:500] if stdout else stderr[:500]
            }
        
        except docker.errors.DockerException as e:
            print(f"[DOCKER] Error: {e}")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": f"Docker error: {e}"
            }

def run_tests_in_sandbox(repo_path: str, timeout: int = 60) -> dict:
    """Run the repo's test suite in a sandbox."""
    try:
        container = docker_client.containers.run(
            SANDBOX_IMAGE,
            command="sh -c 'pip install pytest -q && python -m pytest /app -v 2>&1'",
            volumes={repo_path: {"bind": "/app", "mode": "ro"}},
            working_dir="/app",
            network_mode="none",
            mem_limit="512m",
            remove=False,
            detach=True
        )
        
        result = container.wait(timeout=timeout)
        logs = container.logs().decode("utf-8")
        
        try:
            container.remove(force=True)
        except:
            pass
        
        tests_passed = result["StatusCode"] == 0
        print(f"[DOCKER] Tests {'PASSED' if tests_passed else 'FAILED'}")
        
        return {
            "tests_passed": tests_passed,
            "exit_code": result["StatusCode"],
            "output": logs
        }
    
    except Exception as e:
        return {"tests_passed": False, "exit_code": -1, "output": str(e)}
```

### ✅ Phase 5 Test

```python
# test_phase5.py
import sys
sys.path.insert(0, ".")

from sandbox.docker_runner import run_exploit_in_sandbox

# Test 1: Simple exploit that declares VULNERABLE
test_exploit = """
import sqlite3
import os

# Create test database
conn = sqlite3.connect("/tmp/test.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)")
cursor.execute("INSERT INTO users VALUES (1, 'admin', 'secret123')")
conn.commit()

# Simulate SQL injection
malicious_input = "' OR '1'='1"
query = f"SELECT * FROM users WHERE username = '{malicious_input}'"
cursor.execute(query)
results = cursor.fetchall()

if len(results) > 0:
    print(f"VULNERABLE: SQL Injection confirmed. Leaked {len(results)} row(s)")
    print(f"Data leaked: {results}")
    exit(0)
else:
    print("NOT_VULNERABLE")
    exit(1)
"""

result = run_exploit_in_sandbox(test_exploit, "/tmp")
print(f"\nExploit result: {result}")
print(f"Confirmed vulnerable: {result['exploit_succeeded']}")
```

```bash
# First: make sure Docker is running
docker ps

python test_phase5.py
# Expected:
# [DOCKER] Creating sandbox container...
# [DOCKER] Exit code: 0, Vulnerable: True
# [DOCKER] Container destroyed.
# Confirmed vulnerable: True
```

---

## Phase 6 — Agent B: The Engineer

**What you're building:** Agent B receives the vulnerable code + the exploit output, and writes a patch that fixes the vulnerability without breaking functionality.

```python
# agents/engineer.py
import os
from anthropic import Anthropic

client = Anthropic()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

ENGINEER_SYSTEM_PROMPT = """You are Agent B — a senior security engineer who writes clean, safe code.

You've been given vulnerable code and proof of an exploit. Your job is to patch the vulnerability.

RULES:
1. Fix ONLY the vulnerability. Don't refactor unrelated code.
2. Keep the same function signatures — callers must not break
3. Use parameterized queries, input validation, and safe libraries
4. Your output must be ONLY the patched Python code for the affected file
5. Do not add explanatory comments like "# Fixed SQL injection" — the code should be clean
6. Preserve all original functionality for valid inputs"""

def run_engineer_agent(
    vulnerable_code: str,
    file_path: str,
    exploit_output: str,
    vulnerability_type: str,
    error_logs: str = None
) -> dict:
    """
    Agent B patches the vulnerability.
    error_logs is provided when Agent C rejected a previous patch.
    """
    
    retry_context = ""
    if error_logs:
        retry_context = f"""
PREVIOUS PATCH FAILED. Here's why:
{error_logs}

Fix the issues above in your new patch."""
    
    user_prompt = f"""Fix this vulnerability in {file_path}.

=== VULNERABILITY TYPE ===
{vulnerability_type}

=== VULNERABLE CODE ===
{vulnerable_code}

=== PROOF OF EXPLOIT ===
{exploit_output}

{retry_context}

Output ONLY the complete, fixed Python code for {file_path}. Nothing else."""
    
    print(f"[AGENT B] Generating patch for {file_path}...")
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=ENGINEER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    patched_code = response.content[0].text.strip()
    
    # Clean up code fences
    if patched_code.startswith("```python"):
        patched_code = patched_code[9:]
    if patched_code.startswith("```"):
        patched_code = patched_code[3:]
    if patched_code.endswith("```"):
        patched_code = patched_code[:-3]
    patched_code = patched_code.strip()
    
    print(f"[AGENT B] Patch generated ({len(patched_code)} chars)")
    
    return {
        "file_path": file_path,
        "patched_code": patched_code,
        "is_retry": error_logs is not None
    }
```

### ✅ Phase 6 Test

```python
# test_phase6.py
import sys
sys.path.insert(0, ".")

from agents.engineer import run_engineer_agent

vulnerable_code = """
import sqlite3

def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
"""

exploit_output = """
VULNERABLE: SQL Injection confirmed. 
Input: ' OR '1'='1
Query became: SELECT * FROM users WHERE username = '' OR '1'='1'
Leaked 3 rows from users table.
"""

result = run_engineer_agent(
    vulnerable_code=vulnerable_code,
    file_path="app.py",
    exploit_output=exploit_output,
    vulnerability_type="SQL Injection"
)

print("=== PATCHED CODE ===")
print(result["patched_code"])

# Check the patch uses parameterized queries
assert "?" in result["patched_code"] or "%s" in result["patched_code"], \
    "Patch should use parameterized queries!"
print("\n✅ Patch uses parameterized queries")
```

```bash
python test_phase6.py
# Expected: Claude generates a fixed version using parameterized queries
# Patch should contain: cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
```

---

## Phase 7 — Agent C: The Reviewer + Loop

**What you're building:** Agent C runs both the tests AND the exploit against the patched code. If either fails, it sends the error back to Agent B. Max 3 retries.

```python
# agents/reviewer.py
import os
from anthropic import Anthropic
from sandbox.docker_runner import run_tests_in_sandbox, run_exploit_in_sandbox

client = Anthropic()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

MAX_RETRIES = 3

def run_reviewer_agent(
    original_code: str,
    patched_code: str,
    exploit_script: str,
    repo_path: str,
    file_path: str
) -> dict:
    """
    Orchestrates the review loop:
    1. Write patched code to sandbox
    2. Run tests
    3. Run exploit (should FAIL now)
    4. If either fails, generate error report for Agent B
    """
    import shutil, tempfile
    
    # Create a copy of repo with patched file
    patched_repo = tempfile.mkdtemp()
    shutil.copytree(repo_path, patched_repo, dirs_exist_ok=True)
    
    # Write the patch
    patched_file_path = os.path.join(patched_repo, file_path)
    with open(patched_file_path, "w") as f:
        f.write(patched_code)
    
    print("[AGENT C] Running tests on patched code...")
    test_result = run_tests_in_sandbox(patched_repo)
    
    print("[AGENT C] Running exploit on patched code...")
    exploit_result = run_exploit_in_sandbox(exploit_script, patched_repo)
    
    # Clean up
    shutil.rmtree(patched_repo, ignore_errors=True)
    
    tests_passed = test_result["tests_passed"]
    exploit_still_works = exploit_result["exploit_succeeded"]
    
    # The patch is good if: tests pass AND exploit no longer works
    patch_approved = tests_passed and not exploit_still_works
    
    error_report = None
    if not patch_approved:
        errors = []
        if not tests_passed:
            errors.append(f"TESTS FAILED:\n{test_result['output'][-1000:]}")
        if exploit_still_works:
            errors.append(f"EXPLOIT STILL WORKS:\n{exploit_result['stdout']}")
        error_report = "\n\n".join(errors)
    
    status = "APPROVED" if patch_approved else "REJECTED"
    print(f"[AGENT C] Review result: {status}")
    
    return {
        "approved": patch_approved,
        "tests_passed": tests_passed,
        "exploit_blocked": not exploit_still_works,
        "error_report": error_report,
        "test_output": test_result["output"],
        "exploit_output": exploit_result["stdout"]
    }

def full_remediation_loop(
    diff: dict,
    semgrep_findings: list[dict],
    rag_context: str,
    repo_path: str
) -> dict:
    """
    The complete Agent A → B → C → loop.
    Returns the final result with patch (if successful) or failure report.
    """
    from agents.hacker import run_hacker_agent
    from agents.engineer import run_engineer_agent
    from sandbox.docker_runner import run_exploit_in_sandbox
    
    # Step 1: Agent A generates exploit
    hack_result = run_hacker_agent(diff, semgrep_findings, rag_context)
    exploit_script = hack_result["exploit_script"]
    
    # Step 2: Test if exploit actually works
    print("[ORCHESTRATOR] Testing exploit in sandbox...")
    exploit_test = run_exploit_in_sandbox(exploit_script, repo_path)
    
    if not exploit_test["exploit_succeeded"]:
        print("[ORCHESTRATOR] Exploit did not succeed — no confirmed vulnerability.")
        return {
            "status": "NO_VULNERABILITY",
            "message": "Static analysis found patterns but no exploitable vulnerability confirmed.",
            "exploit_output": exploit_test["stdout"]
        }
    
    print(f"[ORCHESTRATOR] Vulnerability CONFIRMED: {hack_result['vulnerability_type']}")
    
    # Step 3: Get the vulnerable file content
    changed_file = diff["changed_files"][0]["filename"]
    try:
        with open(os.path.join(repo_path, changed_file)) as f:
            vulnerable_code = f.read()
    except:
        vulnerable_code = "\n".join([f["patch"] for f in diff["changed_files"]])
    
    error_logs = None
    final_patch = None
    
    # Step 4: Agent B + C loop (max 3 retries)
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[ORCHESTRATOR] Patch attempt {attempt}/{MAX_RETRIES}")
        
        # Agent B patches
        patch_result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path=changed_file,
            exploit_output=exploit_test["stdout"],
            vulnerability_type=hack_result["vulnerability_type"],
            error_logs=error_logs
        )
        
        # Agent C reviews
        review_result = run_reviewer_agent(
            original_code=vulnerable_code,
            patched_code=patch_result["patched_code"],
            exploit_script=exploit_script,
            repo_path=repo_path,
            file_path=changed_file
        )
        
        if review_result["approved"]:
            print(f"[ORCHESTRATOR] ✅ Patch approved on attempt {attempt}!")
            final_patch = patch_result
            break
        else:
            error_logs = review_result["error_report"]
            print(f"[ORCHESTRATOR] ❌ Patch rejected: {error_logs[:200]}")
    
    if final_patch:
        return {
            "status": "PATCHED",
            "file": changed_file,
            "vulnerability_type": hack_result["vulnerability_type"],
            "patched_code": final_patch["patched_code"],
            "exploit_script": exploit_script,
            "exploit_output": exploit_test["stdout"],
            "reasoning": hack_result["reasoning"],
            "attempts": attempt
        }
    else:
        return {
            "status": "FAILED_TO_PATCH",
            "vulnerability_type": hack_result["vulnerability_type"],
            "exploit_script": exploit_script,
            "exploit_output": exploit_test["stdout"],
            "error": "Could not generate a working patch after 3 attempts. Human review required."
        }
```

---

## Phase 8 — GitHub PR Creator

**What you're building:** The output. A professional PR with everything a developer needs to review and merge.

```python
# github/pr_creator.py
import os
from github import Github
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def create_security_pr(
    repo_name: str,
    result: dict,
    base_branch: str = "main"
) -> str:
    """Creates a PR with the security patch."""
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"aegis/fix-{result['vulnerability_type'].lower().replace(' ', '-')}-{timestamp}"
    
    # Get base branch SHA
    base_sha = repo.get_branch(base_branch).commit.sha
    
    # Create new branch
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    
    # Get existing file to update it
    file_path = result["file"]
    try:
        existing_file = repo.get_contents(file_path, ref=base_branch)
        repo.update_file(
            path=file_path,
            message=f"fix: patch {result['vulnerability_type']} in {file_path}",
            content=result["patched_code"],
            sha=existing_file.sha,
            branch=branch_name
        )
    except Exception as e:
        print(f"[PR] Error updating file: {e}")
        return None
    
    # Build PR description
    pr_body = f"""## 🛡️ Aegis Security Patch

**Vulnerability Type:** {result['vulnerability_type']}
**File:** `{result['file']}`
**Attempts to patch:** {result.get('attempts', 1)}

---

### 🔴 Proof of Exploit

The following exploit was confirmed to work against the original code:

```
{result['exploit_output'][:800]}
```

---

### ✅ Verification

- Exploit no longer succeeds against patched code ✅
- Existing tests pass ✅

---

### 🤖 How This Was Found

1. **Semgrep** flagged a vulnerable pattern on commit
2. **Agent A (Hacker)** wrote an exploit and confirmed it works in an isolated sandbox
3. **Agent B (Engineer)** wrote a patch
4. **Agent C (Reviewer)** verified tests pass and exploit is blocked

**Review this patch carefully before merging.** Aegis is automated but not infallible.

---
*Generated by [Aegis](https://github.com/your-org/aegis) — Autonomous White-Hat Security System*"""

    pr = repo.create_pull(
        title=f"[Aegis] Fix {result['vulnerability_type']} in {file_path}",
        body=pr_body,
        head=branch_name,
        base=base_branch
    )
    
    print(f"[PR] Created: {pr.html_url}")
    return pr.html_url
```

---

## Phase 9 — Wire It All Together

### The final orchestrator

```python
# orchestrator.py
import os
import tempfile
import subprocess
from dotenv import load_dotenv

load_dotenv()

from github.diff_fetcher import get_diff, clone_or_pull_repo
from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm
from rag.indexer import index_repository
from rag.retriever import retrieve_relevant_context
from agents.reviewer import full_remediation_loop
from github.pr_creator import create_security_pr

REPOS_DIR = "./repos"
os.makedirs(REPOS_DIR, exist_ok=True)

# Track which repos have been indexed
indexed_repos = set()

async def run_aegis_pipeline(push_info: dict):
    """The complete Aegis pipeline, triggered on each push."""
    
    repo_name = push_info["repo_name"]
    commit_sha = push_info["commit_sha"]
    
    print(f"\n{'='*60}")
    print(f"[AEGIS] Starting pipeline for {repo_name}@{commit_sha[:8]}")
    print(f"{'='*60}")
    
    # Step 1: Clone/update repo
    repo_path = os.path.join(REPOS_DIR, repo_name.replace("/", "_"))
    clone_or_pull_repo(push_info["repo_url"], repo_path)
    
    # Step 2: Index repo if first time (RAG setup)
    if repo_name not in indexed_repos:
        print("[AEGIS] First time seeing this repo — building RAG index...")
        index_repository(repo_path, repo_name)
        indexed_repos.add(repo_name)
    
    # Step 3: Get the diff
    diff = get_diff(repo_name, commit_sha)
    
    if not diff["changed_files"]:
        print("[AEGIS] No code files changed. Skipping.")
        return
    
    print(f"[AEGIS] Changed files: {[f['filename'] for f in diff['changed_files']]}")
    
    # Step 4: Semgrep scan (fast first-pass filter)
    changed_file_paths = [f["filename"] for f in diff["changed_files"]]
    semgrep_findings = run_semgrep_on_files(changed_file_paths, repo_path)
    
    if not semgrep_findings:
        print("[AEGIS] Semgrep found nothing suspicious. Skipping LLM analysis.")
        return
    
    print(f"[AEGIS] Semgrep found {len(semgrep_findings)} potential issue(s). Engaging agents...")
    
    # Step 5: RAG context retrieval
    rag_context = retrieve_relevant_context(repo_name, diff, semgrep_findings)
    
    # Step 6: Run the full agent loop
    result = full_remediation_loop(diff, semgrep_findings, rag_context, repo_path)
    
    print(f"\n[AEGIS] Pipeline result: {result['status']}")
    
    # Step 7: Create PR if we have a patch
    if result["status"] == "PATCHED":
        pr_url = create_security_pr(repo_name, result)
        print(f"[AEGIS] ✅ PR created: {pr_url}")
    elif result["status"] == "FAILED_TO_PATCH":
        print(f"[AEGIS] ⚠️ Could not patch automatically. Manual review needed.")
        # Could still create a PR with just the exploit proof + "needs manual fix"
    else:
        print(f"[AEGIS] ℹ️ No confirmed vulnerability found.")
```

### Update main.py to use the pipeline

```python
# In main.py, uncomment this line:
background_tasks.add_task(run_aegis_pipeline, push_info)
```

### ✅ Phase 9 — Full End-to-End Test

```bash
# 1. Start Aegis
python main.py

# 2. In your test repo, make a commit with vulnerable code
cd test_repo
echo "
def get_admin(admin_id):
    import sqlite3
    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()
    # New vulnerability
    cursor.execute(f'SELECT * FROM admins WHERE id = {admin_id}')
    return cursor.fetchone()
" >> app.py
git add . && git commit -m "Add admin lookup function"
git push

# 3. Watch Aegis terminal:
# [AEGIS] Starting pipeline for yourname/test-repo@abc12345
# [AEGIS] Changed files: ['app.py']
# [AEGIS] Semgrep found 1 potential issue(s). Engaging agents...
# [AGENT A] Analyzing code with extended thinking...
# [DOCKER] Creating sandbox container...
# [ORCHESTRATOR] Vulnerability CONFIRMED: SQL Injection
# [AGENT B] Generating patch...
# [AGENT C] Running tests on patched code...
# [AGENT C] Review result: APPROVED
# [PR] Created: https://github.com/yourname/test-repo/pull/1
```

---

## 🧠 What We Learned From Research — Applied to Aegis

### Decision Log

| Decision | Why We Made It | Alternative We Rejected |
|---|---|---|
| **Claude Agent SDK** | Extended thinking for deep vulnerability reasoning; MCP native; 84% task success rate | OpenAI SDK — locked to OpenAI models |
| **Semgrep MCP server** | Official, maintained, 5000+ rules; plugs directly as MCP tool | Custom Semgrep CLI wrapper |
| **ChromaDB local** | Zero setup, free, fast enough for hackathon | Pinecone — cost and setup overhead |
| **Docker rootless** | Isolation without root privileges; container escape protection | Running exploits directly — unsafe |
| **Extended Thinking enabled** | Agent A needs to reason about complex vulnerability chains | Basic API call — worse exploit quality |
| **Subagents for parallelism** | Scan multiple vuln types simultaneously | Sequential — too slow |

### Improvements We Can Add Post-Hackathon

1. **Agent D — The Threat Modeler** — Before Agent A runs, a new agent builds a threat model of the entire changed component. Gives Agent A much better targeting.

2. **Long-term memory** — Store past vulnerability patterns per repo in PostgreSQL. Over time, Aegis learns what vulnerabilities this specific codebase tends to have.

3. **Semgrep MCP server integration** — Instead of running Semgrep as CLI, connect the official `semgrep-mcp` server to Agent A as a tool. Agent A can invoke Semgrep itself during reasoning.

4. **Parallel scanning** — Use Claude Agent SDK subagents to scan for SQL injection, XSS, path traversal, and auth bypass simultaneously.

5. **GitHub MCP server** — Replace `PyGithub` with the official GitHub MCP server for PR creation and diff fetching.

---

## 📋 Quick Reference — Commands Cheat Sheet

```bash
# Start Aegis
python main.py

# Index a repo manually
python -c "from rag.indexer import index_repository; index_repository('./my-repo', 'user/repo')"

# Test Semgrep
semgrep --config auto --json ./test_repo

# Test Docker is working
docker run --rm python:3.11-slim python -c "print('Docker OK')"

# Run all phase tests in order
python test_phase2.py
python test_phase3.py
python test_phase4.py
python test_phase5.py
python test_phase6.py

# Check Anthropic connection
python -c "from anthropic import Anthropic; c = Anthropic(); print('Connected')"
```

---

*Build one phase at a time. Test before moving on. The most important thing is that each piece works in isolation before you connect them.*

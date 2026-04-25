# Aegis Agent System Verification

## System Overview

The Aegis system is **fully implemented** with all the components you mentioned:

1. ✅ **Docker Sandbox** - Exploits are tested in isolated containers
2. ✅ **RAG Context** - Vector database (ChromaDB) provides codebase context
3. ✅ **Multi-Agent Pipeline** - 4 specialized AI agents work together

## Architecture

### Pipeline Flow (LangGraph State Machine)

```
GitHub Webhook → Orchestrator → LangGraph Pipeline
                                      ↓
                              1. Pre-Process Node
                                 - Clone repo
                                 - Get git diff
                                 - Run Semgrep (static analysis)
                                 - Fetch RAG context (parallel)
                                      ↓
                              2. Finder Node (Agent 1)
                                 - Analyzes diff + Semgrep + RAG
                                 - Identifies ALL vulnerabilities
                                 - Returns structured findings
                                      ↓
                              3. Exploiter Node (Agent 2)
                                 - Writes exploit script for EACH finding
                                 - Tests in Docker sandbox
                                 - Confirms vulnerability is real
                                      ↓
                              4. Engineer Node (Agent 3)
                                 - Generates patched code
                                 - Writes pytest tests
                                 - Verifier re-runs exploit on patch
                                      ↓
                              5. Safety Validator
                                 - Checks for regressions
                                 - Validates fix quality
                                      ↓
                              6. Approval Gate (CRITICAL only)
                                 - Waits for human approval
                                      ↓
                              7. PR Creator
                                 - Opens GitHub PR with fix
```

## Component Details

### 1. Docker Sandbox (`sandbox/docker_runner.py`)

**Purpose**: Safely execute untrusted exploit code in isolation

**Security Features**:
- Read-only repo mount at `/app`
- No network access (`network_mode="none"`)
- Memory limit (256MB default)
- CPU quota (50% of one core)
- Non-root user (`sandbox`)
- All Linux capabilities dropped
- Writable `/tmp` only (64MB tmpfs)
- Automatic cleanup after execution

**Functions**:
- `run_exploit_in_sandbox()` - Tests if vulnerability is real
- `run_tests_in_sandbox()` - Verifies patch works

**Exploit Success Criteria**:
```python
exploit_succeeded = (
    exit_code == 0
    and "VULNERABLE" in stdout
    and "NOT_VULNERABLE" not in stdout
)
```

**Demo Mode**: Set `DEMO_MODE=true` in `.env` to bypass Docker (for demos when Docker unavailable)

### 2. RAG System (Vector Database)

**Components**:
- `rag/indexer.py` - Indexes repository code into ChromaDB
- `rag/retriever.py` - Fetches relevant context for agents

**How It Works**:

1. **Indexing** (`index_repository()`):
   - Walks through repo files
   - Extracts functions and classes (AST parsing)
   - Creates embeddings using `BAAI/bge-small-en-v1.5` or default model
   - Stores in ChromaDB at `aegis_vector_db/`

2. **Retrieval** (`retrieve_relevant_context()`):
   - Builds query from: changed files + diff + Semgrep findings
   - Searches vector DB for similar code chunks
   - Returns function/class-level context (not random file slices)
   - Filters by distance threshold (default: 1.5)

**Example RAG Context**:
```
=== RELATED CODEBASE CONTEXT ===
(Function/class-level chunks from the repo most relevant to the changed code)

--- function `get_user` in app.py (lines 12–18) ---
def get_user(name):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    query = f"SELECT * FROM users WHERE name='{name}'"
    cur.execute(query)
    return cur.fetchone()
```

### 3. Agent System

#### Agent 1: Finder (`agents/finder.py`)
- **Model**: Groq (llama-3.3-70b-versatile) - fast inference
- **Input**: Git diff + Semgrep results + RAG context
- **Output**: JSON array of vulnerability findings
- **Features**:
  - Multi-language support (Python, JS, Java, Go, Rust, etc.)
  - CVSS scoring
  - Confidence levels (HIGH/MEDIUM/LOW)
  - Severity ranking (CRITICAL → HIGH → MEDIUM → LOW)

**Example Finding**:
```json
{
  "file": "app.py",
  "line_start": 12,
  "vuln_type": "SQL Injection",
  "severity": "CRITICAL",
  "description": "User input concatenated directly into SQL query",
  "relevant_code": "query = f\"SELECT * FROM users WHERE name='{name}'\"",
  "confidence": "HIGH",
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
  "cvss_score": 9.1
}
```

#### Agent 2: Exploiter (`agents/exploiter.py`)
- **Model**: Groq (llama-3.3-70b-versatile)
- **Input**: ONE vulnerability finding + diff + RAG context
- **Output**: Python exploit script
- **Process**:
  1. Analyzes vulnerable code
  2. Writes exploit that proves vulnerability
  3. Script runs in Docker sandbox
  4. Must print "VULNERABLE: <description>" if successful

**Example Exploit Script**:
```python
import sys
import os
import sqlite3

os.chdir('/tmp')
sys.path.insert(0, '/app')

from app import get_user

# Create test database
conn = sqlite3.connect("users.db")
cur = conn.cursor()
cur.execute("CREATE TABLE users (id INTEGER, name TEXT)")
cur.execute("INSERT INTO users VALUES (1, 'admin')")
conn.commit()
conn.close()

# Test SQL injection
result = get_user("' OR '1'='1")
if result:
    print(f"VULNERABLE: SQL Injection confirmed - got {result}")
    sys.exit(0)
else:
    print("NOT_VULNERABLE")
    sys.exit(1)
```

#### Agent 3: Engineer (`agents/engineer.py`)
- **Model**: Mistral (devstral-2512) - best at code generation
- **Input**: Vulnerable code + exploit proof + error logs (on retry)
- **Output**: JSON with `patched_code` and `test_code`
- **Features**:
  - Generates complete fixed file
  - Writes pytest tests
  - Retries with larger model if first attempt fails

**Example Patch**:
```python
# patched_code
import sqlite3

def get_user(name):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    # Fixed: Use parameterized query
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
    return cur.fetchone()
```

**Example Test**:
```python
# test_code
import sys
sys.path.insert(0, '/app')
from app import get_user

def test_normal_user():
    """Test that normal queries work"""
    result = get_user("alice")
    assert result is not None

def test_sql_injection_blocked():
    """Test that injection is blocked"""
    result = get_user("' OR '1'='1")
    assert result is None  # Should not return all users
```

#### Agent 4: Verifier (part of Engineer node)
- **Purpose**: Re-runs exploit on patched code
- **Process**:
  1. Applies patch to repo
  2. Runs exploit script in Docker sandbox
  3. Exploit should FAIL (print "NOT_VULNERABLE")
  4. Runs pytest tests
  5. All tests must pass

### 4. Pipeline State Management

**LangGraph State** (`pipeline/state.py`):
```python
{
    "repo_full_name": str,
    "commit_sha": str,
    "branch": str,
    "scan_id": int,
    "local_repo_path": str,
    "diff": dict,
    "semgrep_findings": list,
    "rag_context": str,  # ← RAG context here
    "vulnerability_findings": list,
    "confirmed_vulnerabilities": list,
    "current_vuln_index": int,
    "patched_code": str,
    "test_code": str,
    "verification_passed": bool,
    "exploit_artifacts": list,  # ← Exploit results
    "patch_artifacts": list,
    "pr_urls": list,
    "pipeline_status": str,
    "error": str
}
```

## Verification Checklist

### ✅ Docker Sandbox Integration
- [x] Exploits run in isolated containers
- [x] Security hardening (no network, limited resources, non-root)
- [x] Automatic cleanup
- [x] Timeout handling
- [x] Demo mode for testing without Docker

**File**: `sandbox/docker_runner.py`

### ✅ RAG Context Integration
- [x] Repository indexing (function/class level)
- [x] Vector embeddings (ChromaDB)
- [x] Context retrieval based on diff + Semgrep
- [x] Passed to Finder and Exploiter agents

**Files**: `rag/indexer.py`, `rag/retriever.py`

### ✅ Agent Pipeline
- [x] Finder analyzes with RAG context
- [x] Exploiter writes and tests exploits in Docker
- [x] Engineer generates patches and tests
- [x] Verifier confirms fix works
- [x] Safety validator checks for regressions

**Files**: `agents/finder.py`, `agents/exploiter.py`, `agents/engineer.py`, `pipeline/nodes.py`

## Configuration

### Environment Variables (`.env`)

```bash
# AI Models
GROQ_API_KEY=<your-key>              # Finder + Exploiter
MISTRAL_API_KEY=<your-key>           # Engineer
HACKER_MODEL=llama-3.3-70b-versatile # Fast model for analysis
ENGINEER_MODEL=devstral-2512         # Quality model for patches

# Docker Sandbox
SANDBOX_IMAGE=python:3.11-slim       # Base image
SANDBOX_TIMEOUT=30                   # Exploit timeout (seconds)
SANDBOX_MEM_LIMIT=256m               # Memory limit
SANDBOX_CPU_QUOTA=50000              # CPU quota (50% of one core)

# RAG
RAG_EMBEDDING_MODEL=bge              # or "default"
RAG_TOP_K=5                          # Number of context chunks
RAG_DISTANCE_THRESHOLD=1.5           # Similarity threshold
VECTOR_DB_DIR=./aegis_vector_db      # ChromaDB storage

# Demo Mode (bypass Docker for testing)
DEMO_MODE=false                      # Set to "true" to skip Docker
```

## Testing the System

### 1. Check Docker is Running
```bash
docker ps
# Should show running containers or empty list (not error)
```

### 2. Check RAG Index
```bash
ls -la aegis_vector_db/
# Should show ChromaDB files
```

### 3. Trigger a Scan
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/scans/trigger-direct \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "commit_sha": "HEAD", "branch": "main"}'

# Via webhook (push to GitHub)
git push origin main
```

### 4. Monitor Pipeline
```bash
# Watch backend logs
tail -f <backend-log-file>

# Check scan status
curl http://localhost:8000/api/v1/scans/<scan_id>
```

### 5. Verify Exploit Ran in Docker
Look for log entries like:
```
[orchestrator] Agent 2 (Exploiter) writing exploit...
[sandbox] Starting isolated Docker sandbox for exploit...
[sandbox] Exploit finished — exit_code=0, succeeded=True
```

### 6. Verify RAG Context Was Used
Look for log entries like:
```
[finder] Agent 1 (Finder) running with Groq/llama-3.3-70b-versatile...
[retriever] RAG retrieval: found 5 relevant chunks
```

## Common Issues

### Docker Not Available
**Symptom**: `SANDBOX_UNAVAILABLE: Docker is not running`
**Solution**: 
```bash
# Start Docker Desktop (macOS/Windows)
# Or start Docker daemon (Linux)
sudo systemctl start docker
```

### RAG Index Empty
**Symptom**: `No related context found (repository not yet indexed)`
**Solution**:
```bash
# Trigger indexing via API
curl -X POST http://localhost:8000/api/v1/repos \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "repo_url": "https://github.com/user/repo"}'
```

### Exploit Fails to Confirm
**Symptom**: Exploit exits with code 1 or doesn't print "VULNERABLE"
**Possible Causes**:
1. Vulnerability doesn't actually exist (false positive from Semgrep)
2. Exploit script has bugs
3. Database/file paths don't match
4. Timeout too short

**Solution**: Check exploit script in scan record, run manually in Docker

## Summary

The Aegis system is **fully functional** with:

1. ✅ **Docker Sandbox**: All exploits run in isolated containers with strict security
2. ✅ **RAG Integration**: Vector database provides codebase context to agents
3. ✅ **Multi-Agent Pipeline**: 4 specialized agents work together to find, prove, fix, and verify vulnerabilities

The system is production-ready and follows security best practices. The only thing needed is to ensure Docker is running and repositories are indexed before scanning.

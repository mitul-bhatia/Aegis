# 🛡️ Aegis System Architecture

**Last Updated**: April 23, 2026  
**Status**: Production Ready

---

## Overview

Aegis is an autonomous white-hat vulnerability remediation system that uses a 4-agent AI architecture to automatically detect, exploit, patch, and verify security vulnerabilities in GitHub repositories.

---

## System Flow

```
GitHub Push
    ↓
Webhook Handler (main.py)
    ↓
Orchestrator (orchestrator.py)
    ↓
┌─────────────────────────────────────────────┐
│ 1. Clone Repo + Get Diff                   │
│ 2. Semgrep Scan                             │
│    └─ Status: "scanning"                    │
│                                             │
│ 3. Agent 1 (Finder): Identify ALL vulns    │
│    └─ Returns: List[VulnerabilityFinding]  │
│    └─ Status: "scanning" (with details)    │
│                                             │
│ 4. For each finding:                        │
│    ├─ Agent 2 (Exploiter): Write exploit   │
│    │  └─ Status: "exploiting"              │
│    ├─ Docker: Test exploit                 │
│    └─ If confirmed: Continue               │
│       └─ Status: "exploit_confirmed"       │
│                                             │
│ 5. Agent 3 (Engineer): Patch + Tests        │
│    └─ Returns: patched_code + test_code    │
│    └─ Status: "patching"                   │
│                                             │
│ 6. Agent 4 (Verifier): Verify fix           │
│    ├─ Test patch in Docker                 │
│    ├─ Run exploit on patched code          │
│    ├─ If exploit fails: Success!           │
│    └─ Update RAG with patched code         │
│       └─ Status: "verifying"               │
│                                             │
│ 7. Create PR                                │
│    └─ Status: "fixed" (with pr_url)        │
└─────────────────────────────────────────────┘
    ↓
SSE Broadcast to Frontend
```

---

## 4-Agent Architecture

### Agent 1: Finder
**File**: `agents/finder.py`  
**Model**: Codestral-2508  
**Purpose**: Identifies ALL vulnerabilities from diff + RAG context

**Input**:
- Git diff (changed files)
- Semgrep findings
- RAG context (codebase knowledge)

**Output**:
```python
List[VulnerabilityFinding]:
  - file: str
  - line_start: int
  - vuln_type: str
  - severity: str (CRITICAL, HIGH, MEDIUM, LOW)
  - description: str
  - relevant_code: str
  - confidence: str (HIGH, MEDIUM, LOW)
```

**Key Features**:
- JSON parsing with retry logic
- Severity sorting
- Pydantic models for type safety

---

### Agent 2: Exploiter
**File**: `agents/exploiter.py`  
**Model**: Codestral-2508  
**Purpose**: Takes ONE vulnerability → writes exploit → proves it's real

**Input**:
- Single VulnerabilityFinding
- Git diff
- RAG context

**Output**:
```python
{
  "exploit_script": str,  # Python script
  "vulnerability_type": str,
  "reasoning": str
}
```

**Key Features**:
- Focuses on single vulnerability
- Generates runnable Python exploits
- Tests actual code from /app in Docker

---

### Agent 3: Engineer
**File**: `agents/engineer.py`  
**Model**: Devstral-2512  
**Purpose**: Generates patch + unit tests

**Input**:
- Vulnerable code
- Exploit output
- Vulnerability type
- Error logs (if retry)

**Output**:
```python
{
  "patched_code": str,
  "test_code": str,  # pytest format
  "file_path": str,
  "is_retry": bool
}
```

**Key Features**:
- Generates both patch AND tests
- Uses parameterized queries for SQL injection
- Maintains function signatures
- Fallback if JSON parsing fails

---

### Agent 4: Verifier
**File**: `agents/reviewer.py`  
**Purpose**: Verifies fix + updates RAG

**Input**:
- Vulnerable code
- Exploit script
- Repo path
- Repo name

**Output**:
```python
{
  "success": bool,
  "patched_code": str,
  "test_code": str,
  "attempts": int
}
```

**Key Features**:
- Runs remediation loop (max 3 attempts)
- Tests patch in Docker
- Re-runs exploit on patched code
- Updates RAG if successful
- Non-fatal RAG update

---

## Core Components

### Orchestrator
**File**: `orchestrator.py`

**Responsibilities**:
- Coordinates 4-agent pipeline
- Real-time DB status updates
- SSE broadcasts
- Error handling

**Status Flow**:
```
queued → scanning → exploiting → exploit_confirmed → 
patching → verifying → fixed
```

**Alternative Endings**:
- `clean` - No vulnerabilities found
- `false_positive` - Exploit failed
- `failed` - Pipeline error

---

### Docker Sandbox
**File**: `sandbox/docker_runner.py`  
**Image**: `aegis-sandbox:latest`

**Features**:
- Isolated exploit execution
- No network access
- Non-root user
- Mounted code at /app
- Timeout protection

**Functions**:
- `run_exploit_in_sandbox()` - Test exploits
- `run_tests_in_sandbox()` - Run pytest tests

---

### RAG System

#### Indexer
**File**: `rag/indexer.py`  
**Database**: ChromaDB

**Features**:
- AST-based code parsing
- Function/class extraction
- Semantic embeddings
- Incremental updates

#### Retriever
**File**: `rag/retriever.py`

**Features**:
- Semantic code search
- Context retrieval for agents
- Relevance scoring

---

### Semgrep Scanner
**File**: `scanner/semgrep_runner.py`

**Features**:
- Docker fallback (Python 3.14 incompatibility)
- Pattern-based vulnerability detection
- Feeds into Finder agent

---

### GitHub Integration

#### Webhook Handler
**File**: `main.py`

**Features**:
- Signature verification
- Push event handling
- Background pipeline execution

#### PR Creator
**File**: `github_integration/pr_creator.py`

**Features**:
- Creates PR with:
  - Exploit proof
  - Patch diff
  - Test code
  - Vulnerability description

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  github_id INTEGER UNIQUE,
  github_username TEXT,
  github_avatar_url TEXT,
  github_token TEXT,
  created_at TIMESTAMP
);
```

### Repos Table
```sql
CREATE TABLE repos (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  full_name TEXT,
  webhook_id INTEGER,
  is_indexed BOOLEAN,
  status TEXT,
  created_at TIMESTAMP
);
```

### Scans Table
```sql
CREATE TABLE scans (
  id INTEGER PRIMARY KEY,
  repo_id INTEGER,
  commit_sha TEXT,
  branch TEXT,
  status TEXT,
  vulnerability_type TEXT,
  severity TEXT,
  vulnerable_file TEXT,
  exploit_output TEXT,
  patch_diff TEXT,
  pr_url TEXT,
  error_message TEXT,
  created_at TIMESTAMP,
  completed_at TIMESTAMP
);
```

---

## API Endpoints

### Authentication
- `POST /api/auth/github` - OAuth callback
- `GET /api/auth/user/{id}` - Get user info

### Repositories
- `POST /api/repos` - Add repository
- `GET /api/repos` - List repositories
- `GET /api/repos/{id}` - Get repository
- `DELETE /api/repos/{id}` - Delete repository

### Scans
- `GET /api/scans` - List scans
- `GET /api/scans/{id}` - Get scan
- `GET /api/scans/live` - SSE stream

### Webhook
- `POST /webhook` - GitHub webhook

---

## Frontend Architecture

### Dashboard
**File**: `aegis-frontend/app/dashboard/page.tsx`

**Features**:
- Real-time SSE connection
- Repo cards with status
- Scan feed with live updates
- Add repo modal

### Components

#### VulnCard
**File**: `aegis-frontend/components/VulnCard.tsx`

**Features**:
- Status badge (animated)
- Severity badge
- Collapsible sections:
  - Exploit Output
  - Patch Diff
  - Error Details
- PR button

#### AddRepoModal
**File**: `aegis-frontend/components/AddRepoModal.tsx`

**Features**:
- Progress indicator:
  1. Validating
  2. Installing webhook
  3. Indexing codebase
- Real-time polling
- Auto-close on complete

---

## Configuration

### Environment Variables
```bash
# Backend (.env)
MISTRAL_API_KEY=your_key
GITHUB_TOKEN=your_token
GITHUB_WEBHOOK_SECRET=your_secret
DATABASE_URL=sqlite:///aegis.db

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Models
- **Finder**: codestral-2508
- **Exploiter**: codestral-2508
- **Engineer**: devstral-2512
- **Verifier**: Uses Engineer + Docker

---

## Deployment

### Backend
```bash
cd Aegis
source .venv/bin/activate
./start-backend.sh
```

### Frontend
```bash
cd Aegis/aegis-frontend
npm run dev
```

### Docker Sandbox
```bash
cd Aegis
./build-sandbox.sh
```

---

## Security Features

1. **Isolated Execution**: All exploits run in Docker sandbox
2. **No Network Access**: Sandbox has no internet
3. **Non-root User**: Exploits run as non-privileged user
4. **Timeout Protection**: 30s timeout for exploits
5. **Signature Verification**: GitHub webhook signatures verified
6. **Token Encryption**: GitHub tokens encrypted in production

---

## Performance

- **RAG Indexing**: ~2-5 seconds per repo
- **Semgrep Scan**: ~1-3 seconds
- **Agent 1 (Finder)**: ~5-10 seconds
- **Agent 2 (Exploiter)**: ~10-15 seconds per finding
- **Agent 3 (Engineer)**: ~10-15 seconds
- **Agent 4 (Verifier)**: ~5-10 seconds
- **Total Pipeline**: ~30-60 seconds per vulnerability

---

## Error Handling

1. **Retry Logic**: Engineer retries up to 3 times
2. **Non-fatal Failures**: RAG update failures don't break pipeline
3. **Graceful Degradation**: Falls back to Semgrep if agents fail
4. **Status Tracking**: All failures logged in database
5. **SSE Broadcasts**: Frontend notified of all status changes

---

## Testing

### Component Tests
- `test-aegis-components.py` - All 6 components
- Individual agent tests

### Integration Tests
- 4-agent pipeline test
- SSE endpoint test
- Database status updates

### End-to-End Tests
- Real GitHub push
- PR creation
- Frontend live updates

---

## Monitoring

### Logs
- `logs/aegis.log` - Application logs
- Agent execution logs
- Pipeline status logs

### Database
- Scan status tracking
- Error messages
- Performance metrics

### SSE Stream
- Real-time status updates
- Frontend monitoring

---

**Architecture Status**: ✅ Production Ready  
**Last Tested**: April 23, 2026  
**Version**: 1.0.0

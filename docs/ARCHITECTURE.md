# 🏗️ Aegis Architecture

This document provides a comprehensive overview of the Aegis system architecture, design principles, and component interactions.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Principles](#design-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Scalability Considerations](#scalability-considerations)

---

## System Overview

Aegis is an autonomous white-hat security system built on a **4-agent AI pipeline** that automatically detects, exploits, patches, and verifies vulnerabilities in code repositories.

### Key Characteristics

- **Autonomous**: Runs automatically on every commit
- **Proof-Based**: Only fixes vulnerabilities that can be exploited
- **Isolated**: All exploits run in sandboxed Docker containers
- **Learning**: Updates knowledge base after each successful patch
- **Real-Time**: Streams status updates to web dashboard

---

## Design Principles

### 1. Separation of Concerns
Each agent has a single, focused responsibility:
- **Finder**: Identify vulnerabilities
- **Exploiter**: Prove they're real
- **Engineer**: Generate fixes
- **Verifier**: Confirm fixes work

### 2. Fail-Safe Defaults
- Exploits run in isolated containers with no network access
- Non-root user execution
- Memory and CPU limits
- Automatic cleanup on failure

### 3. Proof-of-Concept Required
- Vulnerabilities must be exploitable to be fixed
- Reduces false positives
- Provides concrete evidence for developers

### 4. Continuous Learning
- RAG system updates after each successful patch
- Improves context for future scans
- Learns from past vulnerabilities

### 5. Real-Time Feedback
- SSE streams status updates to frontend
- Developers see progress in real-time
- Transparent pipeline execution

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ Push Event
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Webhook Handler (FastAPI)                   │
│  • Verify HMAC signature                                         │
│  • Extract push info                                             │
│  • Queue pipeline in background                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Pipeline                         │
│                                                                   │
│  1. Clone/Pull Repository                                        │
│  2. Run Semgrep Static Analysis                                  │
│  3. Agent 1 (Finder): Identify ALL vulnerabilities              │
│  4. Agent 2 (Exploiter): Write exploit for each                 │
│  5. Docker Sandbox: Test exploit in isolation                   │
│  6. Agent 3 (Engineer): Generate patch + unit tests             │
│  7. Agent 4 (Verifier): Verify fix + update RAG                 │
│  8. Create GitHub PR with fix, exploit proof, tests             │
│                                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Real-Time SSE Stream                        │
│  • Status updates at each pipeline step                          │
│  • Agent messages and progress                                   │
│  • Exploit output and patch diffs                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend Dashboard                    │
│  • Real-time vulnerability cards                                 │
│  • Status badges and animations                                  │
│  • Exploit output terminal                                       │
│  • Patch diff viewer                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. API Layer (FastAPI)

**File**: `main.py`

**Responsibilities**:
- HTTP request handling
- CORS middleware
- Route registration
- Database initialization
- SSE connection management

**Key Routes**:
- `/webhook/github` - GitHub webhook handler
- `/api/scans/*` - Scan management and SSE
- `/api/repos/*` - Repository management
- `/api/auth/*` - GitHub OAuth

---

### 2. Orchestrator

**File**: `orchestrator.py`

**Responsibilities**:
- Coordinate the 4-agent pipeline
- Update database at each step
- Broadcast SSE events
- Handle errors and retries
- Manage background tasks

**Pipeline Steps**:
1. Clone/pull repository
2. Get diff from GitHub API
3. Run Semgrep static analysis
4. Retrieve RAG context
5. Run Finder agent
6. For each vulnerability:
   - Run Exploiter agent
   - Test exploit in sandbox
   - If exploitable:
     - Run Engineer agent
     - Run Verifier agent (with retry loop)
     - Create GitHub PR
7. Update scan status

---

### 3. Agent System

#### Agent 1: Finder
**File**: `agents/finder.py`  
**Model**: Codestral-2508 (Mistral) or Llama-3.1-70b (Groq)

**Input**:
- Git diff
- Semgrep findings
- RAG context

**Output**:
- `List[VulnerabilityFinding]` with structured data

**Process**:
1. Build prompt with diff + Semgrep + RAG
2. Call LLM with JSON schema
3. Parse JSON response
4. Validate with Pydantic models
5. Sort by severity

---

#### Agent 2: Exploiter
**File**: `agents/exploiter.py`  
**Model**: Codestral-2508 (Mistral) or Llama-3.1-70b (Groq)

**Input**:
- Single vulnerability finding
- Git diff
- RAG context

**Output**:
- Complete Python exploit script

**Process**:
1. Build prompt with vulnerability details
2. Call LLM to generate exploit
3. Clean markdown code fences
4. Return runnable Python code

---

#### Agent 3: Engineer
**File**: `agents/engineer.py`  
**Model**: Devstral-2512 (Mistral)

**Input**:
- Vulnerable code
- Exploit output
- Vulnerability type
- Error logs (if retry)

**Output**:
- JSON with `patched_code` and `test_code`

**Process**:
1. Build prompt with vulnerability + exploit proof
2. Call LLM to generate patch + tests
3. Parse JSON response
4. Validate code syntax
5. Return patch and tests

---

#### Agent 4: Verifier
**File**: `agents/reviewer.py`

**Input**:
- Vulnerable code
- Exploit script
- Patch from Engineer
- Test code from Engineer

**Output**:
- Success/failure status
- Error logs (if failed)

**Process**:
1. Write patched code to disk
2. Run unit tests in Docker sandbox
3. If tests fail → return to Engineer with logs
4. Run exploit on patched code
5. If exploit succeeds → return to Engineer
6. If tests pass AND exploit fails → SUCCESS
7. Update RAG with patched code
8. Return to orchestrator

**Retry Logic**:
- Up to 3 attempts
- Faster model on retries (Codestral-2508)
- Detailed error logs passed to Engineer

---

### 4. Docker Sandbox

**File**: `sandbox/docker_runner.py`

**Security Features**:
- Isolated container with no network access
- Non-root user (`sandbox`)
- Memory limit: 256MB
- CPU quota: 50% of one core
- Timeout: 30 seconds for exploits, 45 seconds for tests
- All capabilities dropped
- Read-only filesystem (except /tmp)

**Functions**:
- `run_exploit_in_sandbox()` - Test exploit
- `run_tests_in_sandbox()` - Run pytest tests

**Fallback**:
- If Docker unavailable, runs locally with subprocess (with warnings)

---

### 5. RAG System

#### Indexer
**File**: `rag/indexer.py`

**Process**:
1. Walk repository directory
2. Extract metadata (functions, classes, imports)
3. Detect SQL/auth/HTTP patterns
4. Create text embeddings
5. Batch upsert to ChromaDB (50 files at a time)

**Metadata Extracted**:
- Functions and classes
- Import statements
- SQL usage flags
- Auth/password flags
- HTTP/API flags

---

#### Retriever
**File**: `rag/retriever.py`

**Process**:
1. Build query from changed files + Semgrep findings
2. Query ChromaDB with cosine similarity
3. Filter by distance threshold (1.5)
4. Return top-K results (default 5)

**Output**:
- Formatted context string for agents
- Includes file paths and code snippets

---

### 6. Scanner

**File**: `scanner/semgrep_runner.py`

**Process**:
1. Resolve Semgrep binary (config → PATH → Homebrew → venv)
2. Run Semgrep with security rules
3. Parse JSON output
4. Normalize findings to standard format

**Fallback**:
- If local Semgrep unavailable, use Docker image

**Output**:
- List of findings with file, line, severity, message

---

### 7. GitHub Integration

#### Webhook Handler
**File**: `github_integration/webhook.py`

**Process**:
1. Verify HMAC-SHA256 signature
2. Extract push info (repo, commit, files)
3. Queue pipeline in background
4. Return 200 OK immediately

---

#### PR Creator
**File**: `github_integration/pr_creator.py`

**Process**:
1. Create branch from base branch
2. Commit patched code
3. Open PR with detailed description
4. Include exploit output and test results

---

#### Diff Fetcher
**File**: `github_integration/diff_fetcher.py`

**Process**:
1. Clone/pull repository
2. Fetch diff from GitHub API
3. Fallback to local file reading if API unavailable

---

### 8. Database Layer

**File**: `database/models.py`

**Tables**:
- **Users**: GitHub OAuth users
- **Repos**: Monitored repositories
- **Scans**: Scan lifecycle tracking

**ORM**: SQLAlchemy with SQLite (swappable to PostgreSQL)

---

### 9. Frontend

**Framework**: Next.js 14 (React + TypeScript)

**Pages**:
- `/dashboard` - Real-time scan list
- `/repos` - Repository management
- `/scans/:id` - Detailed scan view

**Key Features**:
- SSE connection for real-time updates
- Collapsible vulnerability cards
- Status badges with animations
- Exploit output terminal
- Patch diff viewer

---

## Data Flow

### 1. Webhook Event Flow

```
GitHub Push
    ↓
Webhook Handler (verify signature)
    ↓
Extract push info (repo, commit, files)
    ↓
Create Scan record in database (status: QUEUED)
    ↓
Queue orchestrator pipeline in background
    ↓
Return 200 OK to GitHub
```

---

### 2. Pipeline Execution Flow

```
Orchestrator starts
    ↓
Update status: SCANNING
    ↓
Clone/pull repository
    ↓
Run Semgrep static analysis
    ↓
Retrieve RAG context
    ↓
Run Finder agent
    ↓
Update status: EXPLOITING
    ↓
For each vulnerability:
    ↓
    Run Exploiter agent
    ↓
    Test exploit in Docker sandbox
    ↓
    If exploitable:
        ↓
        Update status: EXPLOIT_CONFIRMED
        ↓
        Update status: PATCHING
        ↓
        Run Engineer agent
        ↓
        Update status: VERIFYING
        ↓
        Run Verifier agent (retry loop)
        ↓
        If verified:
            ↓
            Update RAG with patched code
            ↓
            Create GitHub PR
            ↓
            Update status: FIXED
        Else:
            ↓
            Update status: FAILED
    Else:
        ↓
        Update status: FALSE_POSITIVE
    ↓
Broadcast SSE event at each step
```

---

### 3. SSE Update Flow

```
Orchestrator updates scan status
    ↓
Write to database (scans table)
    ↓
Broadcast SSE event
    ↓
Frontend SSE client receives event
    ↓
Update UI in real-time
```

---

## Security Architecture

### 1. Webhook Security
- HMAC-SHA256 signature verification
- Validates `X-Hub-Signature-256` header
- Rejects unsigned webhooks

### 2. Sandbox Security
- Isolated Docker containers
- No network access
- Non-root user execution
- Memory and CPU limits
- Automatic cleanup

### 3. API Security
- GitHub OAuth for authentication
- Token-based authorization
- CORS middleware
- Rate limiting (future)

### 4. Data Security
- GitHub tokens encrypted (production)
- Sensitive data not logged
- Exploit scripts isolated in containers

---

## Scalability Considerations

### Current Architecture
- Single-threaded orchestrator
- SQLite database
- In-memory SSE clients

### Scaling Strategies

#### 1. Horizontal Scaling
- Use Redis for SSE pub/sub
- PostgreSQL for database
- Celery for background tasks
- Load balancer for API

#### 2. Vertical Scaling
- Increase Docker resources
- Optimize LLM calls
- Cache RAG queries

#### 3. Performance Optimizations
- Parallel exploit testing
- Batch RAG indexing
- Connection pooling
- CDN for frontend

---

## Technology Stack

### Backend
- **FastAPI** - Async web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **ChromaDB** - Vector database
- **Docker** - Sandbox isolation
- **Semgrep** - Static analysis
- **Mistral AI** - LLM (Engineer)
- **Groq** - LLM (Finder, Exploiter)

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - Components
- **Server-Sent Events** - Real-time

### Infrastructure
- **SQLite** - Database (dev)
- **Docker** - Containerization
- **GitHub API** - Integration
- **HMAC-SHA256** - Webhook security

---

## Deployment Architecture

### Development
```
Local Machine
├── Backend (FastAPI) - localhost:8000
├── Frontend (Next.js) - localhost:3000
├── SQLite Database - aegis.db
├── ChromaDB - aegis_vector_db/
└── Docker Daemon - sandbox containers
```

### Production
```
Cloud Provider (AWS/GCP/Azure)
├── Load Balancer
├── API Servers (FastAPI) - multiple instances
├── Frontend (Next.js) - CDN + SSR
├── PostgreSQL Database - managed service
├── Redis - SSE pub/sub + caching
├── ChromaDB - persistent volume
└── Docker Hosts - sandbox containers
```

---

## Future Enhancements

### Short-Term
- [ ] Redis for SSE pub/sub
- [ ] PostgreSQL migration
- [ ] Celery for background tasks
- [ ] Rate limiting

### Medium-Term
- [ ] Multi-language support (JavaScript, Java, Go)
- [ ] Custom Semgrep rules
- [ ] Vulnerability prioritization
- [ ] Slack/Discord notifications

### Long-Term
- [ ] Machine learning for vulnerability prediction
- [ ] Automated security testing
- [ ] Integration with CI/CD pipelines
- [ ] Enterprise features (SSO, RBAC, audit logs)

---

## Conclusion

Aegis is built on a solid foundation of modern technologies and best practices. The 4-agent architecture provides clear separation of concerns, while the Docker sandbox ensures security. The RAG system enables continuous learning, and the real-time SSE updates provide transparency.

The system is production-ready and can scale horizontally with minimal changes.

---

**Last Updated**: April 25, 2026  
**Status**: 🟢 Production Ready

# Aegis Architecture Overview

## System Architecture

Aegis is an autonomous security system that monitors GitHub repositories, detects vulnerabilities, generates exploits to confirm them, creates patches, and automatically opens pull requests.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │   FastAPI       │    │   ChromaDB      │
│   Integration   │◄──►│   Backend       │◄──►│   Vector Store  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Webhook       │    │   LangGraph     │    │   RAG System    │
│   Handler       │    │   Pipeline      │    │   Context       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Orchestrator  │    │   7-Agent       │    │   Docker        │
│   Coordinator   │◄──►│   System        │◄──►│   Sandbox       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack

#### Backend Infrastructure
- **FastAPI**: REST API server with async support
- **SQLAlchemy**: Database ORM with SQLite backend
- **LangGraph**: Agent workflow orchestration
- **ChromaDB**: Vector database for RAG context
- **Docker**: Sandboxed exploit execution environment

#### AI/ML Components
- **GROQ**: Ultra-fast LLM inference (Llama-3.3-70b)
- **Mistral**: Specialized coding models (Devstral series)
- **Semgrep**: Static analysis engine with language-specific rules
- **Sentence Transformers**: Code embedding for similarity search

#### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe frontend development
- **Tailwind CSS**: Utility-first styling
- **Shadcn/ui**: Component library

### Data Flow Architecture

```
GitHub Push Event
        │
        ▼
┌─────────────────┐
│ Webhook Handler │ ──► Signature Verification
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Orchestrator   │ ──► Background Task Queue
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ LangGraph       │ ──► State Management
│ Pipeline        │     & Agent Coordination
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Agent Execution │ ──► AI Model Inference
│ (7 Agents)      │     & Docker Sandbox
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ GitHub PR       │ ──► Automated Fix
│ Creation        │     Deployment
└─────────────────┘
```

## Implementation Details

### File Structure
```
aegis/
├── main.py                 # FastAPI application entry point
├── orchestrator.py         # Pipeline coordination logic
├── config.py              # Centralized configuration
├── scheduler.py           # Autonomous scanning scheduler
├── pipeline/
│   ├── graph.py           # LangGraph pipeline definition
│   ├── nodes.py           # Individual pipeline nodes
│   ├── state.py           # Shared state structure
│   └── safety_validator.py # Regression prevention
├── agents/
│   ├── finder.py          # Vulnerability detection agent
│   ├── exploiter.py       # Exploit generation agent
│   ├── engineer.py        # Patch generation agent
│   ├── reviewer.py        # Code review agent
│   ├── reviewer_agent.py  # Alternative reviewer
│   ├── triage.py          # Pre-filtering agent
│   └── schemas.py         # Data structures
├── sandbox/
│   └── docker_runner.py   # Isolated execution environment
├── scanner/
│   └── semgrep_runner.py  # Static analysis integration
├── database/
│   ├── models.py          # SQLAlchemy models
│   └── db.py             # Database connection
├── github_integration/
│   ├── webhook.py         # GitHub webhook handling
│   ├── pr_creator.py      # Pull request automation
│   └── diff_fetcher.py    # Git diff processing
├── rag/
│   ├── indexer.py         # Code indexing for RAG
│   └── retriever.py       # Context retrieval
└── routes/
    ├── repos.py           # Repository management API
    ├── scans.py           # Scan status and results API
    └── auth.py            # Authentication endpoints
```

### Database Schema

#### Core Tables
- **repos**: Repository metadata and indexing status
- **scans**: Individual scan records with status tracking
- **findings**: Vulnerability findings with severity and location
- **patches**: Generated fixes with test results and verification

#### Relationships
```sql
repos (1) ──── (many) scans
scans (1) ──── (many) findings
findings (1) ──── (1) patches
```

### Security Architecture

#### Multi-Layer Security Model
1. **Network Isolation**: Docker containers with no internet access
2. **Resource Limits**: Memory (256MB) and CPU (50%) constraints
3. **User Isolation**: Non-root sandbox user in containers
4. **Capability Dropping**: All Linux capabilities removed
5. **Read-Only Mounts**: Repository code mounted read-only
6. **Signature Verification**: All webhooks cryptographically verified

#### Threat Model
- **Malicious Code Execution**: Contained within Docker sandbox
- **Resource Exhaustion**: Strict timeout and resource limits
- **Data Exfiltration**: No network access from sandbox
- **Privilege Escalation**: Capabilities dropped, no-new-privileges
- **Fork Attacks**: PRs from forks automatically rejected

### Performance Characteristics

#### Measured Performance
- **Semgrep Analysis**: ~3 seconds for typical repository
- **LLM Inference**: 10-20x faster with GROQ vs Mistral
- **Exploit Execution**: 30-second timeout per attempt
- **Patch Generation**: 90-second timeout for complex fixes
- **End-to-End**: 5-15 minutes for complete vulnerability remediation

#### Scalability Limits
- **Single Node**: Current architecture not distributed
- **Memory Usage**: ~2GB for typical scan with RAG context
- **Concurrent Scans**: Limited by Docker daemon capacity
- **Repository Size**: Tested up to ~100k lines of code

### Integration Points

#### External Services
- **GitHub API**: Repository access, webhook delivery, PR creation
- **GROQ API**: Fast LLM inference for analysis tasks
- **Mistral API**: Specialized coding model for patch generation
- **Docker Daemon**: Container orchestration for sandboxing

#### Internal APIs
- **REST Endpoints**: Repository management, scan status, results
- **WebSocket/SSE**: Real-time scan progress updates
- **Database**: Persistent storage of scans, findings, patches
- **File System**: Local repository clones and temporary files

This architecture represents a production-ready implementation of autonomous vulnerability remediation with strong security guarantees and performance optimization.
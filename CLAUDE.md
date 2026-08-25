# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aegis is an autonomous security remediation system — a 7-agent AI swarm that detects, proves, patches, and verifies security vulnerabilities in code, then generates automated Pull Requests.

## Architecture

```
GitHub Webhook → FastAPI (main.py) → Orchestrator (orchestrator.py)
                                              ↓
                                    LangGraph Pipeline (pipeline/graph.py)
                                              ↓
          ┌───────────────┬────────────────────┼────────────────────┐
          ↓               ↓                    ↓                    ↓
       Finder         Exploiter             Engineer          PR Creator
    (RAG Context)   (Sandbox Exploit)    (Patch Gen)        (GitHub API)
```

### Key Files

- `main.py` — FastAPI entry point, webhook handling, route registration
- `config.py` — Centralized environment configuration (import from here, not `os.getenv`)
- `orchestrator.py` — Pipeline entry point, DB status updates, SSE broadcast
- `pipeline/graph.py` — LangGraph state machine with conditional routing
- `pipeline/nodes.py` — Actual implementation of each agent node
- `database/models.py` — SQLAlchemy models (User, Repo, Scan, VulnSignature)
- `github_integration/webhook.py` — GitHub webhook signature verification
- `agents/` — Individual agent implementations (finder, exploiter, engineer, reviewer)

## Commands

### Backend
```bash
# Install dependencies (use project venv)
/Users/mitulbhatia/Desktop/Aegis/.venv/bin/python -m pip install -r requirements.txt

# Start FastAPI server
/Users/mitulbhatia/Desktop/Aegis/.venv/bin/python main.py

# Health check
curl -s http://127.0.0.1:8000/health
```

### Frontend
```bash
cd aegis-frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Testing
```bash
# Run specific test file
/Users/mitulbhatia/Desktop/Aegis/.venv/bin/python -m pytest tests/test_phase2.py

# Run all tests
/Users/mitulbhatia/Desktop/Aegis/.venv/bin/python -m pytest tests/
```

## Development Conventions

1. **Configuration**: Read settings from `config.py` only — never call `os.getenv()` in feature code
2. **Pipeline flow**: Keep pipeline logic centralized in `orchestrator.py` and `pipeline/nodes.py`
3. **Logging**: Use structured logging with scan context — see `slog = get_logger(__name__)` pattern
4. **Security**: Verify before patching, patch before PR, fail closed when unsure
5. **Import conventions**: GitHub integration is `github_integration` package; use `from github import Github` for PyGithub
6. **Minimal changes**: Prefer targeted fixes over broad refactors

## Pipeline Flow

The LangGraph pipeline executes these nodes in sequence:

1. **pre_process** — Clone repo, detect language, run Semgrep
2. **finder** — Use RAG to extract vulnerability contexts
3. **exploiter** — Write and run proof-of-concept exploits in sandbox
4. **engineer** — Generate code patches
5. **safety_validator** — Check for regressions
6. **approval_gate** — Human approval for critical vulns
7. **pr_creator** — Open GitHub PR

## Environment Variables

Key variables (see `.env.example` and `config.py` for full list):
- `MISTRAL_API_KEY`, `GROQ_API_KEY` — AI providers
- `GITHUB_TOKEN` — For automated PR creation
- `GITHUB_WEBHOOK_SECRET` — Secures webhook endpoint
- `DATABASE_URL` — PostgreSQL connection (Supabase in production)
- `DEMO_MODE=true` — Bypasses Docker sandbox for testing

## Notes

- Production uses Supabase PostgreSQL with pgvector for RAG embeddings
- Demo mode (`DEMO_MODE=true`) simulates successful exploits without Docker
- Fork PRs are never scanned (security policy)
- The system runs on free tiers: Vercel (frontend), Render (backend), Supabase (database)
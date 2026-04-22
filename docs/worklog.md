# 🛡️ Aegis — Development Worklog

> This file tracks all development activity, decisions, and progress.
> Updated by the development agent after every significant change.

---

## Session 1 — April 22, 2026

### Context
- Mitul started this session wanting to audit the full codebase and get it running
- Discovered the entire backend pipeline was code-complete but never tested
- Original setup used Anthropic/Claude — switched to Mistral AI (Codestral + Devstral)

### Changes Made

#### 1. Migrated AI Backend: Anthropic → Mistral AI
**Why:** Mitul chose Devstral for the coding agent. Codestral selected for hacker agent (code-focused, cheaper, lighter guardrails for security research).

| File | Change |
|------|--------|
| `config.py` | Replaced `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` with `MISTRAL_API_KEY` / `HACKER_MODEL` / `ENGINEER_MODEL` |
| `agents/hacker.py` | Rewrote from Anthropic SDK → Mistral SDK. Removed extended thinking (Mistral doesn't support it). Import: `from mistralai.client.sdk import Mistral` |
| `agents/engineer.py` | Rewrote from Anthropic SDK → Mistral SDK. Same import fix. |
| `requirements.txt` | `anthropic>=0.39.0` → `mistralai>=1.0.0` |
| `.env.example` | New template with Mistral key + dual model config |
| `tests/test_phase4.py` | Updated reference message |
| `tests/test_phase6.py` | Updated reference message |

**Key discovery:** Mistral SDK v2.4.1 requires `from mistralai.client.sdk import Mistral` (not the top-level package). Model IDs: `codestral-2508` and `devstral-2512`.

#### 2. Configured Environment
- Created `.env` with real API keys (Mistral + GitHub)
- Installed all Python dependencies into `.venv`
- Installed Semgrep separately (not in requirements.txt)
- Fixed OpenTelemetry version conflict between chromadb and semgrep

#### 3. Ran All Phase Tests
| Phase | Result | Notes |
|-------|--------|-------|
| Phase 2 (Semgrep) | ✅ PASS | Found 2 SQL injection findings |
| Phase 3 (RAG) | ✅ PASS | Indexed 2 files, retrieved context |
| Phase 4 (Agent A) | ✅ PASS | Codestral wrote SQLi exploit in 2s |
| Phase 5 (Sandbox) | ✅ PASS | Docker ran exploit, confirmed VULNERABLE |
| Phase 6 (Agent B) | ✅ PASS | Devstral wrote parameterized query patch in 1s |
| Server Health | ✅ PASS | FastAPI /health responds correctly |

#### 4. Identified What's Missing
- **No frontend / UI exists** — the entire user-facing product layer is absent
- **No onboarding flow** — no way for a user to paste a repo URL and configure monitoring
- **No dashboard** — no way to see scan results, vulnerability feed, PR status
- **No persistent storage** — no database tracking repos, findings, history
- Backend pipeline phases 7-9 (reviewer loop, PR creator, orchestrator) are written but untested in a live E2E flow

### Current Model Costs
| Agent | Model | Cost per run |
|-------|-------|-------------|
| Hacker (A) | codestral-2508 | ~$0.00025 |
| Engineer (B) | devstral-2512 | ~$0.00025 |
| **Total** | | **~$0.0005 per vulnerability** |

### Decisions Pending
- [ ] Tech stack for frontend (HTML/JS vs React/Next.js)
- [ ] Single-user vs multi-user for hackathon
- [ ] Dashboard design and features
- [ ] Onboarding flow depth
- [ ] Trigger scope (push only vs PR events too)

---

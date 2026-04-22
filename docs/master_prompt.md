# Aegis — Master Context Prompt

> **Purpose:** Paste this at the start of every new LLM/agent session to give full context.
> **Last updated:** April 22, 2026

---

## THE PRODUCT (what the end user experiences)

1. User visits Aegis web app, signs up via GitHub OAuth
2. User pastes a GitHub repo URL into the onboarding screen
3. Aegis auto-installs a webhook on that repo via GitHub API (no manual steps for user)
4. Aegis builds a RAG index of the entire codebase in the background
5. User sees a dashboard confirming the repo is "monitored"
6. On every commit OR PR to that repo:
   - Aegis scans for vulnerabilities (Semgrep)
   - Exploits any found vulns in an isolated Docker sandbox (proves it's real)
   - Patches the code (Agent B)
   - Verifies the patch works (Agent C, max 3 retries)
   - Raises a GitHub PR with exploit proof + patch
7. User sees all of this live in the dashboard:
   - Repo list with status
   - Live scan feed (streaming or polling)
   - Vulnerability cards (severity, type, file, exploit output, patch diff, PR link)
   - Scan history

---

## ARCHITECTURE: TWO SEPARATE APPS

### App 1: Backend (ALREADY BUILT)
- **Framework:** FastAPI (Python)
- **Location:** Project root `/`
- **Port:** 8000
- **What it does:** Receives webhooks, runs the full agent pipeline
- **AI Stack:** Codestral (hacker) + Devstral (engineer) via Mistral SDK
- **Import:** `from mistralai.client.sdk import Mistral`

### App 2: Frontend (TO BE BUILT)
- **Framework:** Next.js 14+ with React, TypeScript, Tailwind CSS
- **Location:** `aegis-frontend/`
- **Port:** 3000
- **What it does:** GitHub OAuth, onboarding, dashboard, real-time scan feed

---

## BACKEND FILES — EXISTING PIPELINE (do not modify unless genuinely required)

```
├── main.py              # FastAPI entry, webhook receiver
├── orchestrator.py      # Agent pipeline coordinator
├── config.py            # Env vars (MISTRAL_API_KEY, GITHUB_TOKEN, etc.)
├── agents/
│   ├── hacker.py        # Agent A — codestral-2508, writes exploits
│   ├── engineer.py      # Agent B — devstral-2512, writes patches
│   └── reviewer.py      # Agent C — verify + retry loop (max 3)
├── rag/
│   ├── indexer.py       # ChromaDB codebase indexer
│   └── retriever.py     # Semantic context retrieval
├── sandbox/
│   └── docker_runner.py # Isolated Docker execution
├── github_integration/
│   ├── webhook.py       # Signature verification
│   ├── diff_fetcher.py  # Gets diffs from GitHub API
│   └── pr_creator.py    # Opens PRs with proof + patch
└── scanner/
    └── semgrep_runner.py # Semgrep static analysis
```

## NEW BACKEND CODE (to be added as separate modules)

### New API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/repos` | List all monitored repos for a user |
| `POST /api/repos` | Add repo + auto-install webhook + trigger RAG index |
| `DELETE /api/repos/{id}` | Remove repo + uninstall webhook |
| `GET /api/scans` | Scan history (all or per repo) |
| `GET /api/scans/{id}` | Single scan with full detail |
| `GET /api/scans/live` | SSE stream for live scan updates |
| `POST /api/auth/github` | Exchange OAuth code for session |
| `GET /api/user` | Current user info |

### Database (SQLite + SQLAlchemy)

- `users` (id, github_id, github_username, github_token, created_at)
- `repos` (id, user_id, full_name, webhook_id, is_indexed, created_at)
- `scans` (id, repo_id, commit_sha, status, vulnerability_type, exploit_output, patch_diff, pr_url, created_at)

---

## FRONTEND PAGES

- `/` — Landing page
- `/auth/callback` — GitHub OAuth callback
- `/dashboard` — Repo list + scan feed
- `/repos/[id]` — Single repo detail
- `/scans/[id]` — Single scan detail

## FRONTEND COMPONENTS

- `RepoCard` — repo name, status badge, last scan
- `ScanFeed` — live scrolling scan events
- `VulnCard` — severity, type, exploit output, patch diff, PR link
- `AddRepoModal` — repo URL input, setup progress
- `StatusBadge` — scanning / exploiting / patching / verified / failed

---

## TECH DECISIONS

- **Auth:** GitHub OAuth (next-auth frontend, token verify backend)
- **Real-time:** SSE from FastAPI → Next.js (no WebSockets)
- **Styling:** Tailwind + shadcn/ui, dark theme, security aesthetic
- **Database:** SQLite + SQLAlchemy (Postgres post-hackathon)

---

## WHAT "DONE" LOOKS LIKE

User opens Aegis → signs in with GitHub → pastes repo URL → clicks "Monitor" →
Aegis says "Setting up..." → user makes a commit → dashboard shows:
"Scanning... Exploit confirmed (SQL Injection)... Patch generated...
Verified... PR opened" → click PR link → see the actual GitHub PR.

That sequence, working live, is the demo.

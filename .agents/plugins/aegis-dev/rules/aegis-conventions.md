# Aegis 2.0 — Project Conventions

Stack: FastAPI + SQLAlchemy 2.0 (Postgres, SQLite fallback) + LangGraph + Groq
(`openai/gpt-oss-120b`) + Semgrep + Docker sandbox + Next.js 14 frontend.
Deployed: backend on Render, frontend on Vercel.

## Non-negotiable security constraints
- The sandbox container (`backend/runner/Dockerfile.sandbox`) must always keep:
  `cap_drop: ALL`, `network: none`, non-root user, read-only repo mount,
  256MB/50% resource limits. Never relax these to "fix" a failing exploit
  verification — fix the exploit harness instead.
- Webhook signature verification (`github_integration/webhook.py`) is
  mandatory on every inbound GitHub event. Never bypass it for testing —
  use a recorded fixture payload instead.
- PRs from forks are auto-rejected. Don't change this without an explicit
  ask.
- The Engineer Agent's patches must always ship with a pytest regression
  test (`regression_test_code` in its output contract) — a patch without
  one is incomplete, not just under-tested.

## Agent output contracts (don't drift from these silently)
- Finder Agent → `List[VulnerabilityFinding]` with CVSS v3.1 severity,
  exact line numbers, attack vector explanation.
- Engineer Agent → `{patched_file_content, explanation, regression_test_code}`.
- Reviewer Agent → runs `ast.parse()` first; emits `is_safe: true/false`.
  Any change to these schemas must update `agents/schemas.py` AND the
  frontend's TypeScript contract in the same PR — see Task 9 in
  `docs/tasks/PRD.md`.

## Known fragile points (per ARCHITECTURE.md)
- Single-node only — no distributed scan execution yet.
- ~2GB memory per scan with RAG context loaded; watch this on Render's
  free/starter tiers.
- Tested up to ~100k LOC repos — larger repos are unverified territory.

## When a subagent finishes a change
State plainly which of the 4 agent contracts (Finder/Engineer/Reviewer/
PR Creator) or which sandbox constraint it touched, if any. Silence on
this is treated as "nothing security-relevant changed" — so don't be quiet
about it if that's not actually true.

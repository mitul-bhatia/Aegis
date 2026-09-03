---
task: Aegis ship-hardening — production verification loop
test_command: "./test-pipeline.sh"
---

# Task: Aegis Ship Hardening

Bring Aegis 2.0 from "core built + live deploy path" to a verifiable ship candidate.
Read `docs/PROJECT_MEMORY.md`, `AGENTS.md`, `.ralph/guardrails.md`, and `.ralph/progress.md` before every iteration.

Model-agnostic: works under Cursor Agent (Grok / Composer / others). Overnight CLI loops use `cursor-agent` + `RALPH_MODEL`.

## Context

- Backend: `backend/app/` (FastAPI, agents, orchestrator, RAG, GitHub App)
- Frontend: `aegis-frontend/` (Next.js 14)
- Deploy: Render backend + Vercel frontend; secrets in `.env` / dashboards only
- Security: sandbox + webhook verification are non-negotiable
- Coding discipline: Karpathy + engineering-discipline rules in `.cursor/rules/`

## Success Criteria

1. [x] Uncommitted WIP triage: either commit blackbox tests + agent/API cleanup intentionally, or document deferred items in `.ralph/progress.md`
2. [x] `./test-pipeline.sh` (or equivalent e2e) runs and passes locally
3. [x] Blackbox suite green: `./pipeline-test-api.sh`, `./pipeline-test-webhooks.sh`, `./pipeline-test-sandbox.sh`, `./pipeline-test-adversarial.sh` (or note blockers with repro)
4. [x] Backend health smoke: `GET /health` (or `/docs`) against local or Render URL succeeds
5. [x] Auth smoke documented: OAuth / session path does not 500 on cold start (warmup/ping still works)
6. [x] Frontend build succeeds: `cd aegis-frontend && npm run build`
7. [x] Frontend↔backend contract: `aegis-frontend/lib/api.ts` aligns with `/api/v1` routes for auth, repos, scans, approve
8. [x] Webhook signature verification path covered by fixture test (no bypass)
9. [x] Sandbox constraints unchanged and verified (`Dockerfile.sandbox` + isolation test)
10. [x] `docs/PROJECT_MEMORY.md` Stage snapshot updated to ship-candidate / shipped with date
11. [x] No secrets committed; `.env` / `.env.production` remain gitignored
12. [x] Bloat removal pass: document removals (hardcoded webhook secret fallback, dev auth bypasses); revert `docs.zip` binary drift

## Out of scope (do not expand into)

- New product features unrelated to ship hardening
- Relaxing sandbox / webhook / fork-PR policies
- Large refactors "while here"

## Ralph Instructions

1. Work on the next incomplete criterion (marked `[ ]`)
2. Check off completed criteria (`[ ]` → `[x]`)
3. Run the relevant verify command after each meaningful change
4. Commit only when the user asked — otherwise leave a clean diff summary in `.ralph/progress.md`
5. Append lessons to `.ralph/guardrails.md` when you hit a repeated failure
6. When ALL criteria are `[x]`, output: `<ralph>COMPLETE</ralph>`
7. If stuck on the same issue 3+ times, output: `<ralph>GUTTER</ralph>` and stop

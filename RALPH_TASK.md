---
task: Aegis prod auth parity — verify deploy + OAuth sign-off
test_command: "./pipeline-test-api.sh && ./test-pipeline.sh"
---

# Task: Production Auth Parity & OAuth Sign-off

Post ship-hardening follow-up: confirm fail-closed auth is live on Render, complete OAuth browser verification, and close remaining auth-debt.

Read `docs/PROJECT_MEMORY.md`, `AGENTS.md`, `.ralph/guardrails.md`, and `.ralph/progress.md` before every iteration.

## Context

- Root cause of prod 200 on `/auth/me`: pre-hardening `get_current_user_optional()` returned `db.query(User).first()` and `/auth/me` fell back to creating/returning a demo user when unauthenticated.
- Fix landed in `1aed3e1` (security + auth fail-closed). Re-smoke after each deploy.
- Backend: `backend/app/` · Frontend: `aegis-frontend/` · Deploy: Render + Vercel

## Success Criteria

1. [ ] Prod smoke: `curl -s -o /dev/null -w '%{http_code}' https://aegis-wpeu.onrender.com/api/v1/auth/me` → `401` (no cookies/headers)
2. [ ] Prod smoke: response body is `{"detail":"Not authenticated"}` when unauthenticated
3. [ ] Local unit test `backend/tests/test_auth.py` passes (unauthenticated → 401, bearer → 200)
4. [ ] `./pipeline-test-api.sh` passes (blackbox auth expectation)
5. [ ] `./test-pipeline.sh` passes (e2e with explicit Bearer auth seed)
6. [ ] OAuth browser sign-off: login via Vercel frontend → dashboard loads repos → logout → `/auth/me` is 401 in browser devtools
7. [ ] Document OAuth cold-start behavior if Render free tier sleep causes delay (warmup ping path)
8. [ ] Optional cleanup: remove dead `api.getUser()` in `aegis-frontend/lib/api.ts` (calls non-existent `/auth/user/{id}`)
9. [ ] Update `.ralph/progress.md` with prod smoke timestamps and OAuth result
10. [ ] Update `docs/PROJECT_MEMORY.md` Stage snapshot if milestone confirmed shipped

## Out of scope

- Relaxing sandbox / webhook / fork-PR policies
- New product features unrelated to auth verification
- Large refactors

## Ralph Instructions

1. Work on the next incomplete criterion (marked `[ ]`)
2. Check off completed criteria (`[ ]` → `[x]`)
3. Run verify commands after each meaningful change
4. Commit when user asks or when a deploy-worthy fix is ready
5. Append lessons to `.ralph/guardrails.md` on repeated failures
6. When ALL criteria are `[x]`, output: `<ralph>COMPLETE</ralph>`
7. If stuck 3+ times on same issue, output: `<ralph>GUTTER</ralph>` and stop

---
task: Aegis v1 production deployment
test_command: "./pipeline-test-api.sh && ./pipeline-test-webhooks.sh && ./pipeline-test-adversarial.sh && ./pipeline-test-sandbox.sh && .venv/bin/python -m pytest backend/tests/test_auth.py && cd aegis-frontend && npm run build"
---

# Task: Aegis v1 Production Deployment

Ship Aegis 2.0 to production with verified auth, webhooks, pipeline, and documented deploy runbook.

Read `docs/PROJECT_MEMORY.md`, `docs/DEPLOYMENT.md`, `docs/DEPLOYMENT_NEEDS_FROM_USER.md`, `AGENTS.md`, `.ralph/guardrails.md`, and `.ralph/progress.md` before every iteration.

## Context

- Backend: Render (`aegis-wpeu.onrender.com`) · Frontend: Vercel · DB: Supabase Postgres (when configured)
- Fail-closed auth landed in `1aed3e1`; prod `/auth/me` returns 401 when unauthenticated (verified 2026-09-04)
- User must supply GitHub App + cloud credentials — see `docs/DEPLOYMENT_NEEDS_FROM_USER.md`

---

## 1. Automated verification (local + prod smoke)

1. [x] `./pipeline-test-api.sh` — 4/4 blackbox API tests pass
2. [x] `./pipeline-test-webhooks.sh` — 2/2 webhook HMAC tests pass
3. [x] `./pipeline-test-adversarial.sh` — 3/3 adversarial tests pass
4. [x] `./pipeline-test-sandbox.sh` — 1 static pass + 2 Docker skips (no daemon)
5. [x] `./test-pipeline.sh` — 10/10 e2e pipeline tests pass
6. [x] `backend/tests/test_auth.py` — unauthenticated 401 + Bearer 200
7. [x] `cd aegis-frontend && npm run build` — production build passes
8. [x] Prod smoke: `GET https://aegis-wpeu.onrender.com/health` → 200
9. [x] Prod smoke: `GET /api/v1/auth/me` (no cookies) → 401 `{"detail":"Not authenticated"}`
10. [x] Document results in `.ralph/progress.md`

---

## 2. Render backend

11. [ ] Render service exists and auto-deploys from `main`
12. [ ] `DATABASE_URL` set (Supabase Postgres connection string)
13. [ ] `SESSION_SECRET` set (32+ char random string)
14. [ ] `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` set
15. [ ] `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` set
16. [ ] `GITHUB_WEBHOOK_SECRET` set (matches GitHub App webhook config)
17. [ ] `GROQ_API_KEY` set (pipeline LLM calls)
18. [ ] `FRONTEND_URL` set to Vercel production URL
19. [ ] `API_BASE_URL` set to Render backend URL
20. [ ] `RENDER=true` set (production guard)
21. [ ] Root `Dockerfile` build verified (uvicorn on `$PORT`)
22. [ ] CORS: `FRONTEND_URL` + Vercel preview regex cover production domain

---

## 3. Vercel frontend

23. [ ] Vercel project root = `aegis-frontend`
24. [ ] `NEXT_PUBLIC_API_URL` = Render backend URL
25. [ ] `NEXT_PUBLIC_GITHUB_CLIENT_ID` = GitHub OAuth App client ID (if using env override)
26. [ ] `NEXT_PUBLIC_GITHUB_APP_NAME` = GitHub App slug (install link)
27. [ ] Production domain configured and reachable
28. [ ] `next.config.js` rewrite target matches Render backend URL

---

## 4. GitHub App

29. [ ] GitHub App created with correct name/slug
30. [ ] Webhook URL: `https://<render-host>/api/v1/github/webhook` (or `/github/webhook`)
31. [ ] Webhook secret matches `GITHUB_WEBHOOK_SECRET` on Render
32. [ ] OAuth callback URL: `https://<vercel-host>/auth/callback`
33. [ ] Permissions: Contents (read/write), Pull requests (read/write), Metadata (read), Webhooks
34. [ ] Events subscribed: `push`, `pull_request` (minimum)
35. [ ] App installed on target org/user repos

---

## 5. Database & infrastructure

36. [ ] Supabase/Postgres `DATABASE_URL` connectivity from Render (not SQLite in prod)
37. [ ] DB migrations/schema init succeeds on deploy (`init_db` in lifespan)
38. [ ] `REDIS_URL` — optional for v1 (configured in docker-compose; not used in app code yet)

---

## 6. End-to-end manual smoke (browser)

39. [ ] OAuth: login via Vercel → lands on dashboard
40. [ ] Link repo: GitHub App install → repo appears in dashboard
41. [ ] Scan: trigger scan → findings appear → status `awaiting_approval`
42. [ ] Approve: approve finding → Phase 2 runs → PR URL returned
43. [ ] Logout: `/api/v1/auth/me` → 401 in browser devtools
44. [ ] Document Render cold-start behavior if free tier sleep causes delay

---

## 7. Security & cleanup

45. [x] Webhook HMAC enforced (no missing-signature bypass)
46. [x] Sandbox constraints intact (`cap_drop ALL`, `network: none`)
47. [x] No secret values in repo or docs
48. [x] Remove dead `api.getUser()` in `aegis-frontend/lib/api.ts`
49. [ ] Remove or env-override hardcoded `GITHUB_CLIENT_ID` fallback in `aegis-frontend/app/page.tsx`

---

## 8. Documentation

50. [x] `docs/DEPLOYMENT.md` — step-by-step v1 deploy runbook (env names only)
51. [x] `docs/DEPLOYMENT_NEEDS_FROM_USER.md` — credential checklist for user
52. [x] `README.md` — link to deployment docs
53. [ ] Update `docs/PROJECT_MEMORY.md` Stage snapshot when v1 shipped
54. [ ] Optional: `render.yaml` or deploy script (not present yet)

---

## Out of scope

- Relaxing sandbox / webhook / fork-PR policies
- New product features unrelated to v1 deploy
- Large refactors

## Ralph Instructions

1. Work on the next incomplete criterion (marked `[ ]`)
2. Check off completed criteria (`[ ]` → `[x]`)
3. Run `test_command` after each meaningful change
4. Commit when deploy-worthy fix is ready; push only with user permission
5. Append lessons to `.ralph/guardrails.md` on repeated failures
6. When ALL criteria are `[x]`, output: `<ralph>COMPLETE</ralph>`
7. If stuck 3+ times on same issue, output: `<ralph>GUTTER</ralph>` and stop

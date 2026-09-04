# Aegis v1 Production Deployment Runbook

> **Secrets:** Env var **names** only. Never paste values into docs, commits, or chat logs.

**Last updated:** 2026-09-04

---

## Architecture

| Component | Host | Path / notes |
|-----------|------|--------------|
| Backend API | Render | Root `Dockerfile` → `uvicorn backend.app.main:app` on `$PORT` |
| Frontend | Vercel | Root directory: `aegis-frontend` |
| Database | Supabase Postgres | `DATABASE_URL` on Render |
| GitHub App | github.com/settings/apps | Webhooks + OAuth + repo access |
| LLM | Groq | `GROQ_API_KEY` on Render |

**Live URLs (verify in dashboards — may rotate):**
- Backend: `https://aegis-wpeu.onrender.com`
- Frontend: Vercel production domain (e.g. `https://aegis-ecru-eta.vercel.app`)

---

## Pre-deploy checklist

Run locally before claiming ship-ready:

```bash
./pipeline-test-api.sh
./pipeline-test-webhooks.sh
./pipeline-test-adversarial.sh
./pipeline-test-sandbox.sh
./test-pipeline.sh
.venv/bin/python -m pytest backend/tests/test_auth.py
cd aegis-frontend && npm run build
```

Prod smoke (no auth):

```bash
curl -s https://aegis-wpeu.onrender.com/health
curl -s -o /dev/null -w '%{http_code}\n' https://aegis-wpeu.onrender.com/api/v1/auth/me
# Expect: 200 health, 401 auth/me
```

---

## Step 1 — Supabase / Postgres

1. Create a Supabase project (or any managed Postgres).
2. Copy the **connection string** (pooler or direct).
3. Set on Render as `DATABASE_URL` (use `postgresql://` form; app normalizes `postgres://`).

Verify: Render deploy logs show `Database schemas initialized.` without fatal errors.

---

## Step 2 — Render backend

1. **New Web Service** → connect GitHub repo → branch `main`.
2. **Build:** Docker (uses root `Dockerfile`).
3. **Health check path:** `/health`
4. Set environment variables (names only — see `docs/DEPLOYMENT_NEEDS_FROM_USER.md`):

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | Postgres connection |
| `SESSION_SECRET` | Yes | Session signing (32+ chars) |
| `GITHUB_APP_ID` | Yes | GitHub App numeric ID |
| `GITHUB_APP_PRIVATE_KEY` | Yes | PEM (single line or multiline) |
| `GITHUB_CLIENT_ID` | Yes | OAuth client ID |
| `GITHUB_CLIENT_SECRET` | Yes | OAuth client secret |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook HMAC secret |
| `GROQ_API_KEY` | Yes | LLM for Finder/Engineer/Reviewer |
| `FRONTEND_URL` | Yes | Vercel production URL (CORS) |
| `API_BASE_URL` | Yes | This Render service URL |
| `RENDER` | Yes | Set to `true` |
| `GROQ_MODEL` | No | Default in `config.py` |
| `GROQ_ENGINEER_MODEL` | No | Default in `config.py` |
| `GEMINI_API_KEY` | No | Optional alternate LLM |
| `REDIS_URL` | No | Not used in app code yet (docker-compose only) |
| `CLI_API_KEY` | No | Local sandbox CLI auth |
| `SEMGREP_TIMEOUT` | No | Scanner timeout (default 60s) |

5. Deploy and confirm:
   - `GET /health` → 200
   - `GET /api/v1/auth/me` → 401 (fail-closed)

**CORS:** `backend/app/main.py` allows `FRONTEND_URL`, localhost, and `https://*.vercel.app`. Add a custom domain to `FRONTEND_URL` or extend `origins` if not on Vercel.

---

## Step 3 — Vercel frontend

1. Import repo → set **Root Directory** to `aegis-frontend`.
2. Framework preset: Next.js 14.
3. Environment variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Yes | Render backend URL |
| `NEXT_PUBLIC_GITHUB_CLIENT_ID` | Recommended | OAuth (avoid hardcoded fallback) |
| `NEXT_PUBLIC_GITHUB_APP_NAME` | Recommended | Install link slug |
| `NEXT_PUBLIC_BACKEND_URL` | No | Alternate backend base |

4. Deploy and open production URL.

**Note:** `aegis-frontend/next.config.js` hardcodes `BACKEND_URL` for API rewrites. Keep it in sync with Render URL, or refactor to env-based rewrites.

---

## Step 4 — GitHub App

1. Create GitHub App at https://github.com/settings/apps/new
2. **Webhook URL:** `https://<render-host>/api/v1/github/webhook`
3. **Webhook secret:** generate → set same value as `GITHUB_WEBHOOK_SECRET` on Render
4. **Callback URL:** `https://<vercel-host>/auth/callback`
5. **Permissions (minimum):**
   - Repository: Contents (Read & write)
   - Repository: Pull requests (Read & write)
   - Repository: Metadata (Read-only)
6. **Subscribe to events:** `push`, `pull_request`
7. Generate and download private key → set as `GITHUB_APP_PRIVATE_KEY` on Render
8. Note App ID → `GITHUB_APP_ID`
9. Create OAuth credentials → `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
10. Install app on target account/repos

Test webhook delivery from GitHub App settings → Recent Deliveries should show 200.

---

## Step 5 — Manual E2E smoke

1. Open Vercel production URL
2. **Login** with GitHub OAuth → dashboard loads
3. **Install GitHub App** if prompted → link a test repo
4. **Trigger scan** → wait for `awaiting_approval`
5. **Approve** a finding → verify Phase 2 runs and PR URL appears
6. **Logout** → confirm `/api/v1/auth/me` returns 401 in Network tab

**Cold start:** Render free/starter tier may sleep; first request can take ~25s. Frontend warms backend via proxy before OAuth exchange.

---

## Step 6 — Security verification

- Webhook without signature → 403 (verified by `pipeline-test-webhooks.sh`)
- Unauthenticated `/auth/me` → 401 (verified by `test_auth.py` + prod smoke)
- Payload > 1MB → 413 (verified by adversarial suite)
- Sandbox: `cap_drop ALL`, `network: none` — do not relax (`backend/runner/Dockerfile.sandbox`)
- Fork PRs: not scanned (policy in webhook handler)

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `/auth/me` returns 200 with user JSON | Stale Render deploy; redeploy after auth hardening |
| OAuth 500 | Missing `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` on Render |
| Webhook 403 | `GITHUB_WEBHOOK_SECRET` mismatch with GitHub App |
| CORS errors | `FRONTEND_URL` wrong or custom domain not in CORS list |
| Scan hangs / no findings | Missing `GROQ_API_KEY` or rate limit (429) |
| DB errors on startup | Invalid `DATABASE_URL` or Supabase IP allowlist |

---

## Related docs

- `docs/DEPLOYMENT_NEEDS_FROM_USER.md` — what the operator must provide
- `docs/PROJECT_MEMORY.md` — canonical stage + env var reference
- `RALPH_TASK.md` — deployment checkbox criteria

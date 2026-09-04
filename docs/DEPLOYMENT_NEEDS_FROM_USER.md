# Deployment: What We Need From You

> Fill in values in your **Render / Vercel / GitHub dashboards** — do not paste secrets into chat or commit them to the repo.

Use this checklist to unblock v1 production deployment. The Ralph agent can verify everything else once these are set.

---

## 1. GitHub App

Create at: https://github.com/settings/apps/new

| Item | Where to set | Env var on Render |
|------|--------------|-------------------|
| App name / slug | GitHub App settings | `NEXT_PUBLIC_GITHUB_APP_NAME` on Vercel |
| App ID (numeric) | GitHub App → About | `GITHUB_APP_ID` |
| Private key (.pem) | Generate in App settings | `GITHUB_APP_PRIVATE_KEY` |
| Webhook URL | `https://aegis-wpeu.onrender.com/api/v1/github/webhook` | — |
| Webhook secret (you generate) | GitHub App → Webhook | `GITHUB_WEBHOOK_SECRET` |
| OAuth client ID | GitHub App → Identifiers | `GITHUB_CLIENT_ID` + `NEXT_PUBLIC_GITHUB_CLIENT_ID` |
| OAuth client secret | GitHub App → Client secrets | `GITHUB_CLIENT_SECRET` |
| OAuth callback URL | `https://<your-vercel-domain>/auth/callback` | — |
| App installed on repos | GitHub → Install App | — |

**Permissions needed:** Contents (R/W), Pull requests (R/W), Metadata (R), Webhooks.

**Events:** `push`, `pull_request`.

---

## 2. Render (backend)

Dashboard: https://dashboard.render.com → your Aegis web service → Environment

| Env var | You provide |
|---------|-------------|
| `DATABASE_URL` | Supabase Postgres connection string |
| `SESSION_SECRET` | Random 32+ character string |
| `GITHUB_APP_ID` | From GitHub App |
| `GITHUB_APP_PRIVATE_KEY` | PEM contents |
| `GITHUB_CLIENT_ID` | From GitHub App |
| `GITHUB_CLIENT_SECRET` | From GitHub App |
| `GITHUB_WEBHOOK_SECRET` | Same as GitHub App webhook secret |
| `GROQ_API_KEY` | From https://console.groq.com |
| `FRONTEND_URL` | Your Vercel production URL (e.g. `https://aegis-ecru-eta.vercel.app`) |
| `API_BASE_URL` | `https://aegis-wpeu.onrender.com` (or your Render URL) |
| `RENDER` | `true` |

**Optional:** `GROQ_MODEL`, `GROQ_ENGINEER_MODEL`, `GEMINI_API_KEY`, `CLI_API_KEY`, `SEMGREP_TIMEOUT`

---

## 3. Vercel (frontend)

Dashboard: https://vercel.com → your project → Settings → Environment Variables

| Env var | You provide |
|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://aegis-wpeu.onrender.com` |
| `NEXT_PUBLIC_GITHUB_CLIENT_ID` | GitHub OAuth client ID |
| `NEXT_PUBLIC_GITHUB_APP_NAME` | GitHub App slug (for install links) |

**Project settings:**
- Root directory: `aegis-frontend`
- Production domain (custom or `*.vercel.app`)

---

## 4. Supabase / Postgres

| Item | You provide |
|------|-------------|
| Project created | https://supabase.com |
| Connection string | Set as `DATABASE_URL` on Render |
| Network access | Allow Render outbound (Supabase pooler usually works) |

---

## 5. Groq (LLM)

| Item | You provide |
|------|-------------|
| API key | https://console.groq.com → set as `GROQ_API_KEY` on Render |

---

## 6. Manual verification (after secrets are set)

Reply with **checkmarks only** (no secret values):

- [ ] GitHub App created and installed on test repo
- [ ] Render env vars set and service redeployed
- [ ] Vercel env vars set and frontend redeployed
- [ ] Webhook test delivery shows 200 in GitHub App → Recent Deliveries
- [ ] OAuth login works on production frontend
- [ ] Test scan completes to `awaiting_approval`
- [ ] Approve flow opens a GitHub PR

---

## 7. Optional / not required for v1

| Item | Notes |
|------|-------|
| `REDIS_URL` | In docker-compose; not used by backend app code yet |
| Custom domain | Update `FRONTEND_URL` + CORS + OAuth callback |
| `render.yaml` | Not in repo; manual Render setup works |

---

## What the agent already verified (no secrets needed)

- All local test suites green (2026-09-04)
- Prod `GET /health` → 200
- Prod `GET /api/v1/auth/me` → 401 (fail-closed)
- Frontend `npm run build` passes
- Webhook HMAC + sandbox constraints enforced in code

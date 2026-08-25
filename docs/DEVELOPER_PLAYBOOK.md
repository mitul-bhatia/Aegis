# 📖 Aegis 2.0 — Developer Playbook & Setup Guide

This playbook gives you step-by-step instructions for running, debugging, testing, and customizing Aegis 2.0.

---

## ⚡ 1. Daily Development Commands

### Start the Full Stack (1-Click)
```bash
./run-all.sh
```
- **Web App:** `http://localhost:3000`
- **FastAPI Backend:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`

### Start Individual Services
```bash
# Backend only
./run-backend.sh

# Frontend only
./run-frontend.sh
```

---

## 🧪 2. Running Automated Tests

Run the complete multi-agent pipeline integration test suite:
```bash
./test-pipeline.sh
```
This tests:
1. Health check & DB schema creation.
2. User authentication & GitHub App installation sync.
3. Repository linking.
4. Autonomous scan trigger (`Finder Agent`).
5. Scan status polling & finding extraction.
6. Context injection & patch synthesis (`Engineer Agent`).
7. Safety validation (`Reviewer Agent`).
8. GitHub PR opening (`PR Creator Agent`).
9. SARIF v2.1.0 report generation.
10. Analytics & Scorecard calculations.

---

## 🐳 3. Local Docker Sandbox Exploit Verification

Verify a specific vulnerability finding inside an isolated zero-trust container using Docker Desktop:

```bash
# Verify Scan #1
./verify-docker.sh 1

# Or with custom API URL
python backend/runner/aegis_cli.py verify 1 --api-url http://localhost:8000
```

---

## ⚙️ 4. Environment Variables (`.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string (falls back to SQLite if unreachable) | `postgresql://postgres:postgres@localhost:5432/aegis` |
| `GROQ_API_KEY` | API Key for Groq LLM inference | `gsk_...` |
| `GROQ_MODEL` | Default model for Finder & Reviewer | `openai/gpt-oss-120b` |
| `GITHUB_APP_ID` | GitHub App ID | `154121833` |
| `GITHUB_APP_PRIVATE_KEY` | PEM Private Key for GitHub App | `-----BEGIN RSA PRIVATE KEY-----...` |
| `GITHUB_CLIENT_ID` | OAuth Client ID | `Iv23...` |
| `GITHUB_CLIENT_SECRET` | OAuth Client Secret | `6b2d...` |

---

## 🚀 5. Production Deployment (Render + Vercel)

### Backend (Render):
1. Create a **Web Service** on Render pointing to your repository.
2. Build Command: `pip install -r backend/requirements.txt`
3. Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables: `DATABASE_URL`, `GROQ_API_KEY`, `GITHUB_APP_*`.

### Frontend (Vercel):
1. Import repository to Vercel with Root Directory set to `aegis-frontend`.
2. Framework Preset: `Next.js`.
3. Set `NEXT_PUBLIC_API_URL` to your live Render backend URL (e.g. `https://aegis-backend-kiw7.onrender.com`).

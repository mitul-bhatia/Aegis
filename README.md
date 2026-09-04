# 🛡️ Aegis 2.0 — Autonomous Security Remediation Platform

![Aegis Banner](https://img.shields.io/badge/Aegis-Autonomous%20Security%20Agent-blue?style=for-the-badge&logo=shield)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=flat-square&logo=next.js)
![Docker](https://img.shields.io/badge/Docker-Zero--Trust%20Sandbox-2496ED?style=flat-square&logo=docker)
![Semgrep](https://img.shields.io/badge/Semgrep-SAST%20Rules-00B0FF?style=flat-square)

Aegis is an autonomous AI-driven application security platform that monitors code changes, identifies real vulnerabilities using AST-aware static analysis, enables zero-trust container verification via **Docker Desktop**, and synthesizes verified patches directly as **GitHub Pull Requests**.

---

## ⚡ Key Highlights & Architecture

1. **AST-Aware Structural Codebase RAG:** Lightweight, sub-50ms architectural mapping of repository trees, API route decorators, and class structures.
2. **Autonomous Multi-Agent Loop:**
   - 🔍 **Finder Agent:** Triage SAST signals (Semgrep / OWASP) with Groq LLM reasoning.
   - 🛠️ **Engineer Agent:** Synthesize surgical, minimal code patches with companion regression tests.
   - 🛡️ **Reviewer Agent:** Validate AST syntax and ensure zero regressions or new attack surfaces.
   - 🚀 **PR Creator Agent:** Branch, commit, and open verified GitHub Pull Requests.
3. **Local Docker Sandbox CLI (`aegis_cli.py`):**
   - True zero-trust local verification (`--network none`, `--cap-drop ALL`, non-root user, read-only volume mounts).
   - Real-time terminal output with proof-of-concept exploit verification.

---

## 🚀 Quick Start (Local Development)

### 1. Run with Docker Compose (Recommended)
```bash
docker compose up -d
```
- **Aegis Web Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run Manually
```bash
# Start Backend
cd /Users/mitulbhatia/Desktop/Aegis
.venv/bin/uvicorn backend.app.main:app --reload --port 8000

# Start Frontend (in a separate terminal)
cd aegis-frontend
npm run dev
```

---

## 🛠️ Local Sandbox CLI (DevOps Runner)

Developers can reproduce and verify exploits locally inside an isolated Docker Desktop container:

```bash
# Verify a specific scan finding locally
python backend/runner/aegis_cli.py verify 1 --api-url http://localhost:8000
```

---

## 🧪 Automated Testing

Run the full end-to-end multi-agent pipeline test suite:
```bash
./test-pipeline.sh
./pipeline-test-api.sh
./pipeline-test-webhooks.sh
./pipeline-test-adversarial.sh
./pipeline-test-sandbox.sh
.venv/bin/python -m pytest backend/tests/test_auth.py
```

---

## 🚢 Production Deployment

See **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** for the v1 deploy runbook and **[`docs/DEPLOYMENT_NEEDS_FROM_USER.md`](docs/DEPLOYMENT_NEEDS_FROM_USER.md)** for the credential checklist.

Quick prod smoke:
```bash
curl -s https://aegis-wpeu.onrender.com/health
curl -s -o /dev/null -w '%{http_code}\n' https://aegis-wpeu.onrender.com/api/v1/auth/me
# Expect: 200 health, 401 auth/me
```

<div align="center">

# 🛡️ Aegis — Autonomous Security Remediation System

<p align="center">
  <strong>An autonomous 7-agent AI swarm that detects, proves, patches, and verifies security vulnerabilities in code, generating automated Pull Requests.</strong>
</p>

[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://aegis-frontend-zeta.vercel.app)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://aegis-backend-kiw7.onrender.com/health)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Python](https://img.shields.io/badge/Python-3.11.9-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-blue.style=for-the-badge)](LICENSE)

[🌐 Live Demo](https://aegis-frontend-zeta.vercel.app) • [🔌 Live API Health](https://aegis-backend-kiw7.onrender.com/health) • [📖 Architecture Docs](docs/architecture.md)

</div>

---

## 🚀 Overview

**Aegis** is an autonomous security system inspired by DARPA AIxCC research. When code is pushed or a scan is triggered, Aegis deploys a specialized multi-agent AI pipeline to scan the codebase, isolate vulnerability contexts with RAG, synthesize exploit verification payloads, generate robust code patches, and automatically submit Pull Requests to your repository.

---

## 🌟 Live Demo & Deployments

- **Frontend App (Next.js 14 / Vercel)**: [https://aegis-frontend-zeta.vercel.app](https://aegis-frontend-zeta.vercel.app)
- **Backend API (FastAPI / Render)**: [https://aegis-backend-kiw7.onrender.com](https://aegis-backend-kiw7.onrender.com)
- **PostgreSQL Database (Supabase)**: `db.htlokyrjfhbyevmozuon.supabase.co`

---

## 🏗️ System Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │             GitHub Webhook / User            │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Vercel Edge Network (Frontend)                                                                        │
│  └─ Next.js 14 App Router, Cyberpunk Security Dashboard, SSE Real-Time Event Stream                   │
└─────────────────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                              │ HTTP REST API / SSE
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Render Free Web Service (Backend API)                                                                  │
│  ├─ FastAPI (Python 3.11.9)                                                                             │
│  ├─ Multi-Agent Orchestrator (LangGraph)                                                                │
│  ├─ RAG Vector Search & Chunking Engine (ChromaDB)                                                      │
│  └─ Static Analysis Engine (Semgrep)                                                                    │
└──────────────┬──────────────────────────────┬────────────────────────────────┬──────────────────────────┘
               │                              │                                │
               ▼                              ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────┐
│  Supabase PostgreSQL         │ │  AI Models                   │ │  GitHub API                  │
│  (Database & State Storage)  │ │  (Mistral AI + GROQ)        │ │  (Automated PR Creation)     │
└──────────────────────────────┘ └──────────────────────────────┘ └──────────────────────────────┘
```

---

## 🤖 The 7-Agent AI Swarm

| Agent | Role | AI Model | Function |
| :--- | :--- | :--- | :--- |
| **01. Triage Agent** | Severity Filter | `llama-3.3-70b-versatile` | Filters false positives and prioritizes critical CVEs/vulnerabilities. |
| **02. Finder Agent** | Context Extractor | `codestral-latest` | Uses RAG AST function chunking to extract full vulnerability contexts. |
| **03. Exploiter Agent** | Proof-of-Concept | `llama-3.3-70b-versatile` | Writes executable exploit scripts to prove vulnerability viability. |
| **04. Engineer Agent** | Patch Synthesizer | `codestral-latest` | Generates clean, minimal security fix patches for the code. |
| **05. Safety Validator** | Regression Guard | `mistral-large-latest` | Checks patch logic to ensure zero breaking changes or regressions. |
| **06. Approval Gate** | Policy Enforcer | Rule-Based Engine | Validates repository safety policies and human authorization gates. |
| **07. PR Creator** | Automated Delivery | GitHub REST API | Automatically opens clean GitHub Pull Requests with detailed fix reports. |

---

## 💰 100% Free Production Hosting ($0/Month)

Aegis is engineered to run on permanent $0 free tiers across modern cloud platforms:

- **Frontend**: **Vercel** (Unlimited Next.js Hobby Tier)
- **Backend API**: **Render** (750 free compute hours/month)
- **Database**: **Supabase** (Serverless PostgreSQL)
- **AI Models**: **Mistral AI** & **GROQ** (Free API Tier)

---

## ⚡ Quickstart & Local Development

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**

### 1. Clone & Setup Backend
```bash
git clone https://github.com/mitul-bhatia/Aegis.git
cd Aegis

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Start FastAPI server
python main.py
```

### 2. Setup Frontend
```bash
cd aegis-frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the local dashboard.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` (or configure in Render/Vercel dashboards):

```env
# Database (Supabase / Postgres)
DATABASE_URL=postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres

# AI Provider API Keys
MISTRAL_API_KEY=your_mistral_api_key
GROQ_API_KEY=your_groq_api_key

# GitHub Token (for automatic PR creation)
GITHUB_TOKEN=ghp_your_personal_access_token

# Demo Mode (Set true to test without Docker/Sandbox)
DEMO_MODE=true
AUTO_FALLBACK_TO_DEMO=true

# Server Configuration
PORT=8000
BACKEND_URL=https://aegis-backend-kiw7.onrender.com
FRONTEND_URL=https://aegis-frontend-zeta.vercel.app
```

---

## 📖 Documentation

- 📐 **[Architecture Guide](docs/architecture.md)** — In-depth system design & sequence diagrams
- 🤖 **[Agent Specs](docs/agents.md)** — Prompt designs & multi-agent graph flows
- 🔌 **[API Reference](docs/api.md)** — FastAPI REST endpoints & SSE streaming specifications
- 🚀 **[Deployment Guide](DEPLOYMENT_GUIDE.md)** — Step-by-step production deployment instructions

---

## 🤝 Contributing

Contributions are welcome! Please submit an issue or pull request to help improve Aegis.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

<div align="center">
  <sub>Built with ❤️ for the AI Security Community</sub>
</div>

# 🛡️ Aegis - Autonomous Vulnerability Remediation System

**Autonomous white-hat security system that detects, exploits, patches, and verifies vulnerabilities using a 4-agent AI architecture.**

[![Status](https://img.shields.io/badge/status-production%20ready-green)]()
[![Backend](https://img.shields.io/badge/backend-100%25-green)]()
[![Frontend](https://img.shields.io/badge/frontend-100%25-green)]()

---

## 🎯 What is Aegis?

Aegis is an AI-powered security system that automatically:

1. **Detects** vulnerabilities in your code using Semgrep + AI
2. **Exploits** them in an isolated Docker sandbox to prove they're real
3. **Patches** the code and generates unit tests
4. **Verifies** the fix works and updates its knowledge base
5. **Creates** a GitHub PR with the fix, exploit proof, and tests

All of this happens automatically on every commit, with real-time updates in a web dashboard.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker
- GitHub account

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/aegis.git
cd aegis
```

### 2. Setup Backend
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys:
# - MISTRAL_API_KEY
# - GITHUB_TOKEN
# - GITHUB_WEBHOOK_SECRET
```

### 3. Build Docker Sandbox
```bash
./build-sandbox.sh
```

### 4. Setup Frontend
```bash
cd aegis-frontend
npm install
cp .env.example .env.local
# Edit .env.local if needed
```

### 5. Start Services
```bash
# Terminal 1: Backend
cd Aegis
source .venv/bin/activate
./start-backend.sh

# Terminal 2: Frontend
cd Aegis/aegis-frontend
npm run dev
```

### 6. Access Dashboard
Open http://localhost:3000

---

## 📊 System Architecture

### 4-Agent Pipeline

```
GitHub Push → Webhook → Orchestrator
    ↓
1. Agent 1 (Finder): Identify ALL vulnerabilities
2. Agent 2 (Exploiter): Prove each one is real
3. Agent 3 (Engineer): Generate patch + tests
4. Agent 4 (Verifier): Verify fix + update RAG
    ↓
Create PR → SSE Broadcast to Frontend
```

### Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| **Finder** | Codestral-2508 | Identifies ALL vulnerabilities |
| **Exploiter** | Codestral-2508 | Writes exploits to prove vulnerabilities |
| **Engineer** | Devstral-2512 | Generates patches + unit tests |
| **Verifier** | - | Verifies fixes + updates RAG |

---

## 🎨 Features

### Backend
- ✅ 4-agent AI architecture
- ✅ Docker sandbox for exploit isolation
- ✅ RAG (Retrieval-Augmented Generation) for code context
- ✅ Real-time status updates via SSE
- ✅ Automatic PR creation
- ✅ Unit test generation
- ✅ Semgrep integration

### Frontend
- ✅ Real-time dashboard with SSE
- ✅ Collapsible vulnerability cards
- ✅ Progress tracking for repo setup
- ✅ Status badges with animations
- ✅ Severity indicators
- ✅ PR links

---

## 📁 Project Structure

```
Aegis/
├── agents/                 # 4 AI agents
│   ├── finder.py          # Agent 1: Find vulnerabilities
│   ├── exploiter.py       # Agent 2: Write exploits
│   ├── engineer.py        # Agent 3: Generate patches
│   └── reviewer.py        # Agent 4: Verify fixes
├── sandbox/               # Docker isolation
│   └── docker_runner.py
├── rag/                   # RAG system
│   ├── indexer.py
│   └── retriever.py
├── scanner/               # Semgrep integration
│   └── semgrep_runner.py
├── github_integration/    # GitHub API
│   ├── webhook.py
│   ├── diff_fetcher.py
│   └── pr_creator.py
├── routes/                # API endpoints
│   ├── repos.py
│   └── scans.py
├── database/              # SQLite database
│   ├── models.py
│   └── db.py
├── orchestrator.py        # Main pipeline coordinator
├── main.py                # FastAPI app + webhook handler
└── aegis-frontend/        # Next.js frontend
    ├── app/
    │   └── dashboard/
    └── components/
        ├── VulnCard.tsx
        └── AddRepoModal.tsx
```

---

## 🔧 Configuration

### Backend (.env)
```bash
MISTRAL_API_KEY=your_mistral_api_key
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=sqlite:///aegis.db
REPOS_DIR=./repos
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md) - Complete system architecture
- [Worklog](worklog.md) - Development history
- [Quick Start](QUICK_START.md) - Setup guide

---

## 🧪 Testing

### Run System Tests
```bash
source .venv/bin/activate
python test_clean_system.py
```

### Run Comprehensive Tests
```bash
python run_comprehensive_tests.py
```

### Test SSE Endpoint
```bash
curl -N -m 10 http://localhost:8000/api/scans/live
```

### Test Full Pipeline
1. Add a test repository in the dashboard
2. Push vulnerable code to the repo
3. Watch the dashboard for real-time updates
4. Verify PR is created

---

## 🛠️ Development

### Backend Development
```bash
cd Aegis
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Frontend Development
```bash
cd Aegis/aegis-frontend
npm run dev
```

### Build Docker Sandbox
```bash
./build-sandbox.sh
```

---

## 📊 Status

### Backend
- ✅ 4-agent pipeline
- ✅ Docker sandbox
- ✅ RAG system
- ✅ Real-time updates
- ✅ PR creation
- ✅ Test generation

### Frontend
- ✅ Real-time dashboard
- ✅ SSE connection
- ✅ Vulnerability cards
- ✅ Progress tracking
- ✅ Status badges

### Testing
- ✅ Component tests (test_clean_system.py)
- ✅ Comprehensive tests (run_comprehensive_tests.py)
- ✅ Docker sandbox verified
- ✅ All 10 test scenarios passing (100%)

---

## 🔒 Security

- **Isolated Execution**: All exploits run in Docker sandbox
- **No Network Access**: Sandbox has no internet
- **Non-root User**: Exploits run as non-privileged user
- **Timeout Protection**: 30s timeout for exploits
- **Signature Verification**: GitHub webhook signatures verified

---

## 🤝 Contributing

This is a hackathon project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **Mistral AI** - For Codestral and Devstral models
- **Semgrep** - For static analysis
- **ChromaDB** - For RAG vector database
- **FastAPI** - For backend framework
- **Next.js** - For frontend framework

---

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ for the AI Hackathon**

**Status**: 🟢 Production Ready - Clean Codebase  
**Last Updated**: April 25, 2026

# 🛡️ Aegis - Setup & Running Guide

## Quick Start

### 1. Build the Sandbox (One-time)
```bash
./build-sandbox.sh
```

### 2. Start Backend
```bash
./start-backend.sh
```

### 3. Start Frontend (in a new terminal)
```bash
cd aegis-frontend
npm run dev
```

### 4. Test Everything
```bash
source .venv/bin/activate
python test-complete-system.py
```

---

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop running
- GitHub account

---

## 🔧 Initial Setup

### 1. Install Python Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd aegis-frontend
npm install
cd ..
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `MISTRAL_API_KEY` - Get from https://console.mistral.ai/
- `GITHUB_TOKEN` - Personal access token with `repo` and `admin:repo_hook` scopes
- `GITHUB_CLIENT_ID` - OAuth app client ID
- `GITHUB_CLIENT_SECRET` - OAuth app secret
- `GITHUB_WEBHOOK_SECRET` - Random string for webhook verification

### 4. Build Docker Sandbox
```bash
./build-sandbox.sh
```

---

## 🚀 Running the Application

### Option 1: Using Scripts (Recommended)

**Terminal 1 - Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start-frontend.sh
```

### Option 2: Manual

**Backend:**
```bash
source .venv/bin/activate
python main.py
```

**Frontend:**
```bash
cd aegis-frontend
npm run dev
```

---

## 🧪 Testing

### Test GitHub Token
```bash
source .venv/bin/activate
python test-github-token.py
```

### Test Docker Sandbox
```bash
source .venv/bin/activate
python test-sandbox.py
```

### Test Complete System
```bash
source .venv/bin/activate
python test-complete-system.py
```

---

## 🌐 Access Points

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 📁 Project Structure

```
Aegis/
├── agents/              # AI agents (Hacker, Engineer, Reviewer)
├── database/            # SQLAlchemy models and DB connection
├── github_integration/  # Webhook, diff fetcher, PR creator
├── rag/                 # Vector DB indexing and retrieval
├── routes/              # FastAPI routes (auth, repos, scans)
├── sandbox/             # Docker sandbox runner
├── scanner/             # Semgrep integration
├── aegis-frontend/      # Next.js frontend
├── main.py              # FastAPI entry point
├── orchestrator.py      # Pipeline coordinator
├── config.py            # Configuration
├── Dockerfile.sandbox   # Custom sandbox image
├── start-backend.sh     # Backend startup script
├── start-frontend.sh    # Frontend startup script
└── test-*.py            # Test scripts
```

---

## 🔐 Security Features

### Sandbox Isolation
- Non-root user execution
- No network access
- All Linux capabilities dropped
- No privilege escalation
- Memory and CPU limits
- Automatic container cleanup

### Token Management
- Backend token for webhook installation (full permissions)
- User OAuth token for repo access (limited permissions)
- Proper separation of concerns

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Kill any process on port 8000
lsof -ti:8000 | xargs kill -9

# Restart
./start-backend.sh
```

### Frontend won't start
```bash
# Kill any process on port 3000
lsof -ti:3000 | xargs kill -9

# Restart
./start-frontend.sh
```

### Docker errors
```bash
# Check Docker is running
docker ps

# Rebuild sandbox image
./build-sandbox.sh
```

### "Failed to fetch" error
1. Check backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `main.py`
3. Check browser console for detailed error
4. Verify `.env` has correct `BACKEND_URL=http://localhost:8000`

### Webhook installation fails
1. Verify GitHub token has `admin:repo_hook` permission
2. Run: `python test-github-token.py`
3. Create new token at: https://github.com/settings/tokens
4. Update `GITHUB_TOKEN` in `.env`

---

## 📊 How It Works

1. **User adds repo** → Webhook installed, RAG index built
2. **Developer pushes code** → Webhook fires
3. **Semgrep scans** → Finds potential vulnerabilities
4. **Agent A (Hacker)** → Writes exploit script
5. **Docker Sandbox** → Runs exploit safely
6. **Agent B (Engineer)** → Writes security patch
7. **Agent C (Reviewer)** → Verifies fix works
8. **GitHub PR** → Opened with proof + patch

---

## 🔄 Development Workflow

### Making Changes

Backend changes auto-reload (uvicorn --reload)
Frontend changes auto-reload (Next.js fast refresh)

### Database Changes

```bash
# Reset database
rm aegis.db
python main.py  # Will recreate tables
```

### Sandbox Changes

```bash
# Rebuild after modifying Dockerfile.sandbox
./build-sandbox.sh
```

---

## 📝 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | Yes | Mistral AI API key for agents |
| `GITHUB_TOKEN` | Yes | GitHub PAT with repo + webhook permissions |
| `GITHUB_CLIENT_ID` | Yes | OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | Yes | OAuth app secret |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook signature verification |
| `FRONTEND_URL` | No | Default: http://localhost:3000 |
| `BACKEND_URL` | No | Default: http://localhost:8000 |
| `HACKER_MODEL` | No | Default: codestral-2508 |
| `ENGINEER_MODEL` | No | Default: devstral-2512 |
| `PORT` | No | Default: 8000 |

---

## 🎯 Next Steps

1. ✅ Build sandbox image
2. ✅ Start backend and frontend
3. ✅ Run system tests
4. 🌐 Open http://localhost:3000
5. 🔐 Sign in with GitHub
6. 📦 Add a repository
7. 🐛 Push vulnerable code to test

---

## 📚 Additional Resources

- [Mistral AI Docs](https://docs.mistral.ai/)
- [GitHub Webhooks](https://docs.github.com/en/webhooks)
- [Docker Security](https://docs.docker.com/engine/security/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)

---

**Built for the Autonomous White-Hat Vulnerability Remediation Hackathon**

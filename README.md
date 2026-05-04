# 🛡️ Aegis - AI-Powered Security Scanner

Autonomous security system that finds vulnerabilities, writes exploits to verify them, generates patches, and creates pull requests automatically.

## 🎯 What It Does

1. **Scans** your code with Semgrep
2. **Verifies** vulnerabilities by writing and executing exploits
3. **Generates** patches using AI
4. **Tests** patches to ensure they work
5. **Creates** pull requests automatically

## 🏗️ Architecture

```
GitHub Webhook → Render Backend → Semgrep Scan → AI Agents → Fly.io Sandbox → PR Creation
```

**Render (Main App - FREE):**
- FastAPI backend
- PostgreSQL database
- Next.js frontend
- AI agents (Mistral/GROQ)

**Fly.io (Sandbox - FREE):**
- Docker exploit execution
- Isolated containers
- Patch verification

## 🚀 Quick Start

### Prerequisites
- GitHub account
- Render account (free)
- Fly.io account (free)
- Mistral API key (free tier)
- GROQ API key (free tier)

### Deploy in 30 Minutes

**Full deployment guide:** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Quick steps:**
1. Deploy sandbox to Fly.io (10 min)
2. Deploy main app to Render (15 min)
3. Configure GitHub webhooks (5 min)

## 💰 Cost

**$0/month** (within free tiers)

- Render: 750 hours/month free
- Fly.io: 3 VMs × 256MB free
- Database: Free for 90 days, then $7/month

## 🔧 Local Development

### Setup
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Start backend
python main.py

# Start frontend (in another terminal)
cd aegis-frontend
npm install
npm run dev
```

### Run a Scan
```bash
# Trigger scan via API
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "branch": "main"
  }'
```

## 📊 Features

### Core Features
- ✅ Automated vulnerability scanning (Semgrep)
- ✅ AI-powered exploit generation
- ✅ Isolated exploit execution (Docker)
- ✅ Automatic patch generation
- ✅ Patch verification
- ✅ Pull request creation
- ✅ GitHub webhook integration

### Advanced Features
- ✅ Multi-agent AI system (Finder, Exploiter, Engineer, Reviewer)
- ✅ RAG-based context retrieval
- ✅ Intelligent scheduling
- ✅ Analytics dashboard
- ✅ Real-time scan updates (SSE)
- ✅ Retry logic with exponential backoff
- ✅ Rate limit handling
- ✅ Graceful degradation

## 🔒 Security

### Sandbox Isolation
- No network access
- Memory limits (256MB)
- CPU limits (50%)
- Timeout protection (60s)
- Non-root user
- All capabilities dropped

### API Security
- API key authentication
- GitHub webhook signature verification
- Rate limiting
- Input validation

## 📖 Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Deploy to Render + Fly.io
- [Architecture](docs/architecture.md) - System design
- [API Documentation](docs/api.md) - REST API reference
- [Agents](docs/agents.md) - AI agent system
- [Pipeline](docs/pipeline.md) - Scan pipeline flow

## 🛠️ Tech Stack

**Backend:**
- FastAPI (Python)
- PostgreSQL
- Redis (optional)
- Docker

**Frontend:**
- Next.js 14
- React
- TailwindCSS
- shadcn/ui

**AI:**
- Mistral AI (code generation)
- GROQ (fast inference)
- ChromaDB (vector store)
- LangGraph (agent orchestration)

**Security:**
- Semgrep (static analysis)
- Docker (sandboxing)

## 📈 Roadmap

- [ ] Support for more languages (currently Python-focused)
- [ ] Custom vulnerability rules
- [ ] Slack/Discord notifications
- [ ] PDF report generation
- [ ] Multi-repo dashboard
- [ ] Advanced analytics
- [ ] CI/CD integration (GitHub Actions, GitLab CI)

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- Semgrep for static analysis
- Mistral AI for code generation
- GROQ for fast inference
- Render and Fly.io for free hosting

## 📞 Support

- 🐛 Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/aegis/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/aegis/discussions)

---

**Built with ❤️ for the security community**

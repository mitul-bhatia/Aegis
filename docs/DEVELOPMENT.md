# 🛠️ Aegis Development Guide

**Complete guide for developers working on Aegis**

---

## 📋 Table of Contents

1. [Setup](#setup)
2. [Development Workflow](#development-workflow)
3. [Testing](#testing)
4. [Code Structure](#code-structure)
5. [Adding Features](#adding-features)
6. [Debugging](#debugging)
7. [Deployment](#deployment)

---

## Setup

### Prerequisites
- Python 3.11+ (NOT 3.14 - Semgrep incompatibility)
- Node.js 18+
- Docker Desktop
- GitHub account with personal access token
- Mistral API key

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/aegis.git
cd aegis

# 2. Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your keys

# 5. Build Docker sandbox
./build-sandbox.sh

# 6. Setup frontend
cd aegis-frontend
npm install
cp .env.example .env.local
cd ..

# 7. Initialize database
python -c "from database.db import init_db; init_db()"
```

---

## Development Workflow

### Starting Services

```bash
# Terminal 1: Backend
cd Aegis
source .venv/bin/activate
./start-backend.sh
# Backend runs on http://localhost:8000

# Terminal 2: Frontend
cd Aegis/aegis-frontend
npm run dev
# Frontend runs on http://localhost:3000
```

### Making Changes

#### Backend Changes
1. Edit Python files in `agents/`, `routes/`, etc.
2. Backend auto-reloads (uvicorn --reload)
3. Test changes immediately

#### Frontend Changes
1. Edit TypeScript/React files in `aegis-frontend/`
2. Frontend auto-reloads (Next.js Fast Refresh)
3. Check browser console for errors

#### Agent Changes
1. Edit agent files in `agents/`
2. Update system prompts carefully
3. Test with `test-aegis-components.py`

---

## Testing

### Component Tests

```bash
# Test all 6 components
source .venv/bin/activate
python test-aegis-components.py
```

### Individual Agent Tests

```bash
# Test Finder agent
python -c "from agents.finder import run_finder_agent; ..."

# Test Exploiter agent
python -c "from agents.exploiter import run_exploiter_agent; ..."
```

### API Tests

```bash
# Test SSE endpoint
curl -N -m 10 http://localhost:8000/api/scans/live

# Test scans endpoint
curl http://localhost:8000/api/scans

# Test repos endpoint
curl http://localhost:8000/api/repos?user_id=1
```

### Frontend Tests

```bash
cd aegis-frontend
npm run lint
npm run type-check
```

### Integration Tests

```bash
# Test full pipeline
python test-4-agent-full-pipeline.py
```

---

## Code Structure

### Backend

```
Aegis/
├── agents/                 # AI agents
│   ├── finder.py          # Agent 1: Find vulnerabilities
│   ├── exploiter.py       # Agent 2: Write exploits
│   ├── engineer.py        # Agent 3: Generate patches
│   └── reviewer.py        # Agent 4: Verify fixes
├── sandbox/               # Docker isolation
├── rag/                   # RAG system
├── scanner/               # Semgrep integration
├── github_integration/    # GitHub API
├── routes/                # API endpoints
├── database/              # Database models
├── orchestrator.py        # Pipeline coordinator
├── main.py                # FastAPI app
└── config.py              # Configuration
```

### Frontend

```
aegis-frontend/
├── app/
│   ├── dashboard/         # Dashboard page
│   ├── repos/             # Repo pages
│   └── scans/             # Scan pages
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── VulnCard.tsx       # Vulnerability card
│   └── AddRepoModal.tsx   # Add repo modal
└── lib/
    ├── api.ts             # API client
    └── utils.ts           # Utilities
```

---

## Adding Features

### Adding a New Agent

1. Create file in `agents/`
```python
# agents/new_agent.py
from mistralai.client.sdk import Mistral
import config

client = Mistral(api_key=config.MISTRAL_API_KEY)

SYSTEM_PROMPT = """Your agent's system prompt"""

def run_new_agent(input_data):
    response = client.chat.complete(
        model=config.HACKER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": input_data}
        ]
    )
    return response.choices[0].message.content
```

2. Update `orchestrator.py` to use new agent
3. Add tests
4. Update documentation

### Adding a New API Endpoint

1. Create/edit file in `routes/`
```python
# routes/new_endpoint.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/new-endpoint")
async def new_endpoint():
    return {"message": "Hello"}
```

2. Register in `main.py`
```python
from routes.new_endpoint import router as new_router
app.include_router(new_router)
```

3. Update frontend API client
```typescript
// lib/api.ts
async newEndpoint() {
  const res = await fetch(`${API_BASE}/api/new-endpoint`);
  return res.json();
}
```

### Adding a New Frontend Component

1. Create component file
```typescript
// components/NewComponent.tsx
"use client";

export function NewComponent() {
  return <div>New Component</div>;
}
```

2. Use in page
```typescript
import { NewComponent } from "@/components/NewComponent";
```

---

## Debugging

### Backend Debugging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check Logs
```bash
tail -f logs/aegis.log
```

#### Debug Agent Output
```python
# Add to agent file
print(f"Agent output: {response}")
```

### Frontend Debugging

#### Browser Console
- Open DevTools (F12)
- Check Console tab for errors
- Check Network tab for API calls

#### React DevTools
- Install React DevTools extension
- Inspect component state

### Database Debugging

```bash
# Check database
sqlite3 aegis.db

# List tables
.tables

# Check scans
SELECT * FROM scans ORDER BY created_at DESC LIMIT 5;

# Check repos
SELECT * FROM repos;
```

### Docker Debugging

```bash
# Check running containers
docker ps

# Check sandbox image
docker images | grep aegis-sandbox

# Run exploit manually
docker run --rm -v $(pwd)/test_repo:/app aegis-sandbox:latest python /tmp/exploit.py
```

---

## Common Issues

### Issue: Semgrep fails with Python 3.14
**Solution**: Use Python 3.11 or 3.12, or rely on Docker fallback

### Issue: Docker sandbox not found
**Solution**: Run `./build-sandbox.sh`

### Issue: SSE connection fails
**Solution**: Check CORS settings in `main.py`

### Issue: Agent returns invalid JSON
**Solution**: Check agent system prompt, add retry logic

### Issue: RAG indexing fails
**Solution**: Check ChromaDB installation, verify repo path

---

## Deployment

### Production Checklist

- [ ] Set production environment variables
- [ ] Use production database (PostgreSQL)
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Configure rate limiting
- [ ] Set up monitoring
- [ ] Encrypt GitHub tokens
- [ ] Set up backup system

### Environment Variables

```bash
# Production .env
MISTRAL_API_KEY=prod_key
GITHUB_TOKEN=prod_token
GITHUB_WEBHOOK_SECRET=prod_secret
DATABASE_URL=postgresql://...
ENVIRONMENT=production
```

### Docker Deployment

```bash
# Build backend image
docker build -t aegis-backend .

# Build frontend image
cd aegis-frontend
docker build -t aegis-frontend .

# Run with docker-compose
docker-compose up -d
```

---

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Use `logging` module (not `print`)
- Document functions with docstrings

### TypeScript
- Use TypeScript strict mode
- Define interfaces for all data types
- Use functional components
- Follow React best practices

### Git Commits
- Use conventional commits
- Format: `type(scope): message`
- Examples:
  - `feat(agents): add new finder agent`
  - `fix(frontend): resolve SSE connection issue`
  - `docs(readme): update setup instructions`

---

## Performance Optimization

### Backend
- Use async/await for I/O operations
- Cache RAG results
- Optimize database queries
- Use connection pooling

### Frontend
- Use React.memo for expensive components
- Implement virtual scrolling for long lists
- Optimize bundle size
- Use lazy loading

---

## Security Best Practices

1. **Never commit secrets** - Use .env files
2. **Validate all inputs** - Sanitize user data
3. **Use parameterized queries** - Prevent SQL injection
4. **Verify webhook signatures** - Prevent unauthorized access
5. **Encrypt sensitive data** - Use encryption for tokens
6. **Limit Docker permissions** - Run as non-root
7. **Set timeouts** - Prevent infinite loops

---

## Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Mistral AI Docs](https://docs.mistral.ai/)
- [Docker Docs](https://docs.docker.com/)

### Tools
- [Semgrep](https://semgrep.dev/)
- [ChromaDB](https://www.trychroma.com/)
- [shadcn/ui](https://ui.shadcn.com/)

---

**Last Updated**: April 23, 2026  
**Maintainer**: Aegis Team

# Aegis - Quick Start Guide
**For resuming work after context loss**

## 🚀 Start Everything

```bash
# 1. Start Backend
cd /Users/mitulbhatia/Desktop/Aegis
source .venv/bin/activate
python main.py > backend.log 2>&1 &

# 2. Start Frontend (new terminal)
cd aegis-frontend
npm run dev

# 3. Start Ngrok (new terminal)
ngrok http 8000

# 4. Verify
curl http://localhost:8000/health
```

## 🔍 Check Status

```bash
# Backend health
curl http://localhost:8000/health | python -m json.tool

# Recent scans
sqlite3 aegis.db "SELECT id, status, vulnerability_type FROM scans ORDER BY id DESC LIMIT 5;"

# Monitored repos
sqlite3 aegis.db "SELECT id, full_name, status FROM repos;"

# Backend logs
tail -f backend.log
```

## 🧪 Trigger Test Scan

```bash
curl -X POST "http://localhost:8000/api/v1/scans/trigger-direct?repo_id=4&commit_sha=HEAD&branch=main" \
  -H "Content-Type: application/json" \
  --cookie "session=dummy"
```

## 🐛 Fix Common Issues

### Backend won't start
```bash
pkill -f "python.*main.py"
source .venv/bin/activate
python main.py > backend.log 2>&1 &
```

### Sandbox issues
```bash
docker build -f Dockerfile.sandbox -t aegis-sandbox:latest .
```

### Model errors
Check `.env` has:
```
HACKER_MODEL=llama-3.3-70b-versatile
ENGINEER_MODEL=codestral-latest
```

## 📊 Key Files

- **Context**: `AEGIS_COMPLETE_CONTEXT.md` (full details)
- **Config**: `.env` (API keys, models)
- **Database**: `aegis.db`
- **Logs**: `backend.log`

## 🔑 Important URLs

- Backend: http://localhost:8000
- Frontend: http://localhost:3002
- Ngrok: https://c2cf-115-244-141-202.ngrok-free.app
- Test Repo: https://github.com/Jivit87/aegis-pr-test

## 💡 Remember

1. Groq = Fast (Finder, Exploiter)
2. Mistral = Quality (Engineer)
3. Sandbox needs Flask/Django installed
4. Frontend uses `.data` from paginated responses
5. System prevents duplicate scans for same commit

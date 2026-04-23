# 🛡️ Aegis - Quick Start Guide

## 🚀 Start in 3 Steps

### 1. Build Sandbox (First Time Only)
```bash
./build-sandbox.sh
```

### 2. Start Backend
```bash
./start-backend.sh
```

### 3. Start Frontend (New Terminal)
```bash
./start-frontend.sh
```

## ✅ Verify It Works
```bash
source .venv/bin/activate
python test-complete-system.py
```

## 🌐 Access
- **App:** http://localhost:3000
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs

## 🛠️ Useful Commands

### Stop Services
```bash
# Kill backend
lsof -ti:8000 | xargs kill -9

# Kill frontend
lsof -ti:3000 | xargs kill -9
```

### Test Components
```bash
source .venv/bin/activate

# Test GitHub token
python test-github-token.py

# Test sandbox
python test-sandbox.py

# Test everything
python test-complete-system.py
```

### Rebuild Sandbox
```bash
./build-sandbox.sh
```

### Reset Database
```bash
rm aegis.db
# Restart backend to recreate
```

## 📋 Checklist

- [ ] Docker Desktop running
- [ ] `.env` file configured
- [ ] Sandbox image built
- [ ] Backend started (port 8000)
- [ ] Frontend started (port 3000)
- [ ] Tests passing

## 🐛 Quick Fixes

**Backend won't start:**
```bash
lsof -ti:8000 | xargs kill -9
./start-backend.sh
```

**Frontend won't start:**
```bash
lsof -ti:3000 | xargs kill -9
./start-frontend.sh
```

**Sandbox fails:**
```bash
docker ps  # Check Docker running
./build-sandbox.sh  # Rebuild image
```

**"Failed to fetch":**
- Check backend is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Verify CORS settings

## 📚 Full Documentation
- **Setup:** `README_SETUP.md`
- **Fixes:** `FIXES_APPLIED.md`
- **Status:** `SYSTEM_STATUS.md`

---

**That's it! You're ready to go. 🎉**

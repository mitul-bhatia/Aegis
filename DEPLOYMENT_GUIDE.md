# 🚀 Aegis Deployment Guide - Render + Fly.io

Complete guide to deploy Aegis for **$0/month** using Render (main app) + Fly.io (sandbox).

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│  Render (FREE)                          │
│  ├─ Backend API (FastAPI)              │
│  ├─ PostgreSQL Database                │
│  └─ Frontend (Next.js)                 │
└─────────────────────────────────────────┘
              ↓ HTTP API
┌─────────────────────────────────────────┐
│  Fly.io (FREE)                          │
│  └─ Sandbox Service (Docker execution) │
└─────────────────────────────────────────┘
```

**Cost:** $0/month (within free tiers)

---

## Part 1: Deploy Sandbox to Fly.io (10 minutes)

### Step 1: Install Fly CLI
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### Step 2: Login to Fly.io
```bash
fly auth login
```

### Step 3: Deploy Sandbox Service
```bash
cd sandbox-service

# Create app (first time only)
fly launch --name aegis-sandbox --region sjc --no-deploy

# Generate and set API key
SANDBOX_API_KEY=$(openssl rand -hex 32)
echo "Save this key: $SANDBOX_API_KEY"
fly secrets set SANDBOX_API_KEY=$SANDBOX_API_KEY

# Deploy
fly deploy

# Verify deployment
fly status
fly logs

# Test health endpoint
curl https://aegis-sandbox.fly.dev/health
```

### Step 4: Save Your Sandbox URL and API Key
```bash
# You'll need these for Render deployment
SANDBOX_SERVICE_URL=https://aegis-sandbox.fly.dev
SANDBOX_API_KEY=<the key you generated above>
```

---

## Part 2: Deploy Main App to Render (15 minutes)

### Step 1: Push Code to GitHub
```bash
# If not already done
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/aegis.git
git push -u origin main
```

### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Authorize Render to access your repositories

### Step 3: Deploy from Dashboard

#### Option A: Using render.yaml (Recommended)
1. Click "New +" → "Blueprint"
2. Connect your GitHub repository
3. Render will detect `render.yaml` automatically
4. Click "Apply"

#### Option B: Manual Setup
1. **Create Backend Service:**
   - Click "New +" → "Web Service"
   - Connect repository
   - Name: `aegis-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: `Free`

2. **Create Database:**
   - Click "New +" → "PostgreSQL"
   - Name: `aegis-db`
   - Plan: `Free`
   - Copy the "Internal Database URL"

3. **Create Frontend Service:**
   - Click "New +" → "Web Service"
   - Connect repository
   - Name: `aegis-frontend`
   - Root Directory: `aegis-frontend`
   - Environment: `Node`
   - Build Command: `npm install && npm run build`
   - Start Command: `npm start`
   - Plan: `Free`

### Step 4: Configure Environment Variables

In Render Dashboard → Backend Service → Environment:

**Required:**
```bash
# Sandbox Service (from Part 1)
SANDBOX_SERVICE_URL=https://aegis-sandbox.fly.dev
SANDBOX_API_KEY=<your key from Part 1>

# AI API Keys
MISTRAL_API_KEY=<your Mistral API key>
GROQ_API_KEY=<your GROQ API key>

# GitHub
GITHUB_TOKEN=<your GitHub personal access token>
GITHUB_CLIENT_ID=<your GitHub OAuth app client ID>
GITHUB_CLIENT_SECRET=<your GitHub OAuth app client secret>

# Database (auto-configured if using render.yaml)
DATABASE_URL=<internal database URL from Render>
```

**Optional:**
```bash
DEMO_MODE=false
AUTO_FALLBACK_TO_DEMO=false
GITHUB_WEBHOOK_SECRET=<generate with: openssl rand -hex 32>
```

In Render Dashboard → Frontend Service → Environment:
```bash
NEXT_PUBLIC_BACKEND_URL=https://aegis-backend.onrender.com
```

### Step 5: Deploy
- Render will automatically deploy when you push to GitHub
- Or click "Manual Deploy" → "Deploy latest commit"

### Step 6: Verify Deployment
```bash
# Check backend health
curl https://aegis-backend.onrender.com/health

# Should return:
# {
#   "status": "healthy",
#   "checks": {
#     "database": "healthy",
#     "docker": "unavailable",  # Expected on Render
#     "groq_api": "configured",
#     "mistral_api": "configured",
#     "github_token": "configured"
#   }
# }

# Check frontend
curl https://aegis-frontend.onrender.com
```

---

## Part 3: Configure GitHub Webhooks (5 minutes)

### Step 1: Get Your Webhook URL
```bash
WEBHOOK_URL=https://aegis-backend.onrender.com/webhook/github
```

### Step 2: Configure in GitHub Repository
1. Go to your repository → Settings → Webhooks
2. Click "Add webhook"
3. **Payload URL:** `https://aegis-backend.onrender.com/webhook/github`
4. **Content type:** `application/json`
5. **Secret:** (the GITHUB_WEBHOOK_SECRET from Render env vars)
6. **Events:** Select "Push events" and "Pull requests"
7. Click "Add webhook"

### Step 3: Test Webhook
1. Make a commit to your repository
2. Check Render logs: `Dashboard → Backend → Logs`
3. You should see: `Push received: <commit_sha>`

---

## Part 4: Test End-to-End (5 minutes)

### Test 1: Manual Scan Trigger
```bash
# Trigger a scan via API
curl -X POST https://aegis-backend.onrender.com/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/YOUR_USERNAME/test-repo",
    "branch": "main"
  }'
```

### Test 2: Check Scan Status
```bash
# List all scans
curl https://aegis-backend.onrender.com/api/v1/scans

# Get specific scan
curl https://aegis-backend.onrender.com/api/v1/scans/1
```

### Test 3: View Dashboard
Open in browser:
```
https://aegis-frontend.onrender.com
```

---

## Monitoring & Maintenance

### View Logs

**Render Backend:**
```bash
# In Render Dashboard
Backend Service → Logs
```

**Fly.io Sandbox:**
```bash
fly logs
```

### Check Resource Usage

**Render:**
- Dashboard shows hours used (750 free hours/month)
- Database storage (1GB free)

**Fly.io:**
- Dashboard shows VM usage (3 VMs × 256MB free)

### Update Deployment

**Backend/Frontend:**
```bash
# Just push to GitHub
git add .
git commit -m "Update"
git push

# Render auto-deploys
```

**Sandbox:**
```bash
cd sandbox-service
fly deploy
```

---

## Troubleshooting

### Issue: "Sandbox service unavailable"
**Solution:**
```bash
# Check Fly.io status
fly status

# Check logs
fly logs

# Restart if needed
fly apps restart aegis-sandbox
```

### Issue: "Docker unavailable" in health check
**Expected on Render** - This is normal. The sandbox service handles Docker execution.

### Issue: Render service sleeping (free tier)
**Expected behavior** - Free tier services sleep after 15 minutes of inactivity.
- First request after sleep takes ~30 seconds
- Consider upgrading to paid tier ($7/month) for always-on

### Issue: Database connection errors
**Solution:**
```bash
# Check DATABASE_URL is set correctly
# In Render Dashboard → Backend → Environment
# Should be: postgresql://user:pass@host/dbname
```

### Issue: GitHub webhook not triggering
**Solution:**
1. Check webhook secret matches
2. Check webhook delivery in GitHub: Settings → Webhooks → Recent Deliveries
3. Check Render logs for incoming requests

---

## Cost Breakdown

| Service | Platform | Free Tier | Usage | Cost |
|---------|----------|-----------|-------|------|
| Backend | Render | 750 hrs/month | ~720 hrs | $0 |
| Database | Render | 90 days free | 1GB | $0* |
| Frontend | Render | 750 hrs/month | ~720 hrs | $0 |
| Sandbox | Fly.io | 3 VMs × 256MB | 1 VM | $0 |
| **Total** | | | | **$0/month** |

*After 90 days, database costs $7/month. Alternatives:
- Use SQLite (free forever, but limited features)
- Use Supabase free tier (500MB)
- Use Neon free tier (3GB)

---

## Scaling & Upgrades

### When to Upgrade

**Render Backend ($7/month):**
- Need always-on (no cold starts)
- More than 750 hours/month usage
- Need more CPU/RAM

**Render Database ($7/month):**
- After 90-day free trial
- Need more than 1GB storage
- Need automated backups

**Fly.io ($5-10/month):**
- Need more than 3 VMs
- Need more than 256MB RAM per VM
- Need faster execution

### Free Alternatives

**Database:**
- Supabase (500MB free)
- Neon (3GB free)
- PlanetScale (5GB free)
- SQLite (unlimited, file-based)

**Backend:**
- Railway ($5 credit/month)
- Fly.io (3 VMs free)
- Vercel (serverless functions)

---

## Next Steps

1. ✅ Deploy sandbox to Fly.io
2. ✅ Deploy main app to Render
3. ✅ Configure GitHub webhooks
4. ✅ Test end-to-end
5. 📊 Monitor usage and logs
6. 🔧 Customize for your needs

---

## Support

**Issues?**
- Check logs first (Render Dashboard + `fly logs`)
- Verify environment variables are set
- Test sandbox service independently
- Check GitHub webhook deliveries

**Need Help?**
- Render Docs: https://render.com/docs
- Fly.io Docs: https://fly.io/docs
- GitHub Issues: Create an issue in your repo

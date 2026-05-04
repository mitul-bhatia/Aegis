# Aegis Deployment Guide

## Architecture

- **Frontend**: Next.js on Vercel (Free)
- **Backend**: FastAPI on Render (Free tier with DEMO_MODE)

## ⚠️ Important: DEMO_MODE

Since Render's free tier doesn't support Docker-in-Docker, the backend runs in **DEMO_MODE**:
- ✅ Finder agent works (vulnerability detection)
- ✅ Exploiter agent works (exploit generation)
- ✅ Engineer agent works (patch generation)
- ⚠️ Exploit execution is **simulated** (not run in real sandbox)
- ⚠️ Test verification is **simulated**

**For production with real exploit execution, use:**
- Railway ($5/month credit)
- Oracle Cloud (forever free VMs)
- Self-hosted with Docker

---

## Step 1: Deploy Backend to Render

### 1.1 Create Render Account
1. Go to https://render.com
2. Sign up with GitHub

### 1.2 Create New Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select the Aegis repository

### 1.3 Configure Service
**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt && python -c "from database.db import init_db; init_db()"
```

**Start Command:**
```bash
python main.py
```

**Environment Variables** (Add in Render dashboard):
```
DEMO_MODE=true
MISTRAL_API_KEY=your_mistral_key
GROQ_API_KEY=your_groq_key
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=random_secret_string
GITHUB_CLIENT_ID=your_oauth_client_id
GITHUB_CLIENT_SECRET=your_oauth_client_secret
PORT=8000
FRONTEND_URL=https://your-app.vercel.app
HACKER_MODEL=llama-3.3-70b-versatile
ENGINEER_MODEL=codestral-latest
ENGINEER_RETRY_MODEL=mistral-large-latest
HACKER_TIMEOUT_MS=120000
ENGINEER_TIMEOUT_MS=180000
```

### 1.4 Deploy
1. Click "Create Web Service"
2. Wait for deployment (~5 minutes)
3. Note your backend URL: `https://aegis-backend-xxxx.onrender.com`

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Create Vercel Account
1. Go to https://vercel.com
2. Sign up with GitHub

### 2.2 Import Project
1. Click "Add New..." → "Project"
2. Import your Aegis repository
3. Vercel auto-detects Next.js

### 2.3 Configure Project
**Root Directory:** `aegis-frontend`

**Environment Variables:**
```
NEXT_PUBLIC_BACKEND_URL=https://aegis-backend-xxxx.onrender.com
```

### 2.4 Deploy
1. Click "Deploy"
2. Wait for deployment (~3 minutes)
3. Note your frontend URL: `https://aegis-xxxx.vercel.app`

---

## Step 3: Update Backend with Frontend URL

1. Go to Render dashboard
2. Select your backend service
3. Go to "Environment" tab
4. Update `FRONTEND_URL` to your Vercel URL
5. Save changes (triggers redeploy)

---

## Step 4: Configure GitHub Webhook

### 4.1 Get Webhook URL
Your webhook URL: `https://aegis-backend-xxxx.onrender.com/webhook/github`

### 4.2 Add Webhook to GitHub Repository
1. Go to your GitHub repository
2. Settings → Webhooks → Add webhook
3. **Payload URL**: `https://aegis-backend-xxxx.onrender.com/webhook/github`
4. **Content type**: `application/json`
5. **Secret**: (use the same value as `GITHUB_WEBHOOK_SECRET`)
6. **Events**: Select "Pushes" and "Pull requests"
7. Click "Add webhook"

---

## Step 5: Configure GitHub OAuth (Optional)

### 5.1 Create OAuth App
1. GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. **Application name**: Aegis Security
3. **Homepage URL**: `https://aegis-xxxx.vercel.app`
4. **Authorization callback URL**: `https://aegis-xxxx.vercel.app/auth/callback`
5. Click "Register application"

### 5.2 Update Environment Variables
1. Copy Client ID and Client Secret
2. Update in Render dashboard:
   - `GITHUB_CLIENT_ID`
   - `GITHUB_CLIENT_SECRET`

---

## Step 6: Test Deployment

### 6.1 Check Backend Health
```bash
curl https://aegis-backend-xxxx.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "docker": "unavailable",
    "groq_api": "configured",
    "mistral_api": "configured",
    "github_token": "configured"
  },
  "version": "2.0.0"
}
```

### 6.2 Access Frontend
1. Open `https://aegis-xxxx.vercel.app`
2. You should see the Aegis dashboard
3. Try logging in with GitHub

### 6.3 Test Scan
1. Add a repository
2. Trigger a scan
3. Watch the pipeline execute (in DEMO_MODE)

---

## Troubleshooting

### Backend won't start
- Check Render logs for errors
- Verify all environment variables are set
- Ensure `DEMO_MODE=true`

### Frontend can't connect to backend
- Check `NEXT_PUBLIC_BACKEND_URL` in Vercel
- Verify CORS settings in backend
- Check Render service is running

### Webhook not working
- Verify webhook secret matches
- Check Render logs for webhook requests
- Ensure webhook URL is correct

### Database resets on restart
- Render free tier has ephemeral storage
- Upgrade to paid tier for persistent disk
- Or use external database (PostgreSQL)

---

## Limitations of Free Tier

### Render Free Tier:
- ⚠️ Service sleeps after 15 minutes of inactivity
- ⚠️ 750 hours/month limit
- ⚠️ Ephemeral storage (database resets)
- ⚠️ No Docker support (DEMO_MODE required)

### Vercel Free Tier:
- ✅ Unlimited bandwidth
- ✅ 100GB bandwidth/month
- ✅ Automatic HTTPS
- ✅ Global CDN

---

## Upgrading to Production

For real exploit execution, consider:

### Option 1: Railway ($5/month)
- Full Docker support
- Persistent storage
- No sleep time
- Easy migration from Render

### Option 2: Oracle Cloud (Free Forever)
- 2 VMs free forever
- Full Docker support
- 200GB storage
- Requires manual setup

### Option 3: Self-Hosted
- Full control
- No limitations
- Requires server management

---

## Cost Breakdown

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| Vercel | Unlimited | $20/month |
| Render | 750 hrs/month | $7/month |
| Railway | $5 credit/month | $5+/month |
| Oracle Cloud | 2 VMs forever | Pay as you go |

**Total Free**: $0/month (with limitations)
**Recommended Paid**: $12/month (Railway + Vercel)

---

## Next Steps

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Vercel
3. ✅ Configure webhooks
4. ✅ Test the system
5. 🎯 Monitor usage and upgrade if needed

---

## Support

- Documentation: `/docs` folder
- Issues: GitHub Issues
- API Reference: `https://aegis-backend-xxxx.onrender.com/docs`

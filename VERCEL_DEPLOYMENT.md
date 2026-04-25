# 🚀 Vercel Deployment Guide for Aegis Frontend

## 📋 Current Setup

**Backend (Mac Local):**
- Running on: http://localhost:8000
- Ngrok Tunnel: https://c2cf-115-244-141-202.ngrok-free.app
- Status: ✅ Running (keep Mac awake!)

**Frontend (Vercel):**
- Deployed at: https://aegis-frontend-sigma.vercel.app
- Connects to: Backend via ngrok tunnel

---

## 🔧 Vercel Environment Variables

Add these environment variables in your Vercel project settings:

### **Environment Variables to Add:**

```
NEXT_PUBLIC_API_URL=https://c2cf-115-244-141-202.ngrok-free.app
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23li7vdknIS2ZtxxOH
```

### **How to Add in Vercel:**

1. Go to your Vercel project: https://vercel.com/mitul-bhatias-projects/aegis-frontend
2. Click **Settings** → **Environment Variables**
3. Add each variable:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://c2cf-115-244-141-202.ngrok-free.app`
   - **Environments**: Select "Production" and "Preview"
   
4. Add second variable:
   - **Key**: `NEXT_PUBLIC_GITHUB_CLIENT_ID`
   - **Value**: `Ov23li7vdknIS2ZtxxOH`
   - **Environments**: Select "Production" and "Preview"

5. Click **Save**

---

## 📁 Vercel Build Settings

Based on your screenshot, configure these settings:

### **Root Directory:**
```
aegis-frontend
```

### **Build and Output Settings:**

- **Build Command**: (leave default or use `npm run build`)
- **Output Directory**: (leave default or use `.next`)
- **Install Command**: (leave default or use `npm install`)

### **Framework Preset:**
- Select: **Next.js**

---

## 🔄 GitHub OAuth Configuration

Your OAuth app is already configured correctly:

✅ **Application name**: aegis
✅ **Homepage URL**: https://aegis-frontend-sigma.vercel.app
✅ **Authorization callback URL**: https://aegis-frontend-sigma.vercel.app/auth/callback
✅ **Client ID**: Ov23li7vdknIS2ZtxxOH
✅ **Client Secret**: (already in backend .env)

---

## 🚀 Deployment Steps

### **Option 1: Deploy via Vercel Dashboard**

1. Go to your Vercel project
2. Click **Deployments** tab
3. Click **Redeploy** on the latest deployment
4. Select **Use existing Build Cache** (optional)
5. Click **Redeploy**

### **Option 2: Deploy via Git Push**

```bash
cd aegis-frontend
git add .
git commit -m "Update environment variables for production"
git push origin main
```

Vercel will automatically deploy when you push to main branch.

### **Option 3: Deploy via Vercel CLI**

```bash
cd aegis-frontend
npm install -g vercel
vercel --prod
```

---

## ⚠️ Important Notes

### **Keep Your Mac Running:**
- ✅ Backend is running on your Mac (localhost:8000)
- ✅ Ngrok tunnel is active (https://c2cf-115-244-141-202.ngrok-free.app)
- ⚠️ **DO NOT let your Mac sleep** - the backend needs to stay running
- ⚠️ **Keep ngrok running** - if it stops, update the URL in Vercel

### **If Ngrok URL Changes:**
If you restart ngrok and get a new URL:

1. Update `NEXT_PUBLIC_API_URL` in Vercel environment variables
2. Update `BACKEND_URL` in backend `.env` file
3. Redeploy frontend on Vercel
4. Restart backend server

### **Testing the Deployment:**

1. Visit: https://aegis-frontend-sigma.vercel.app
2. Click "Sign in with GitHub"
3. Authorize the app
4. You should see the dashboard
5. Try adding a repository

---

## 🔍 Troubleshooting

### **Frontend can't connect to backend:**
- Check if ngrok is still running: `curl https://c2cf-115-244-141-202.ngrok-free.app/health`
- Check if backend is running: `curl http://localhost:8000/health`
- Verify environment variables in Vercel are correct

### **OAuth not working:**
- Verify callback URL matches: https://aegis-frontend-sigma.vercel.app/auth/callback
- Check GitHub OAuth app settings
- Ensure NEXT_PUBLIC_GITHUB_CLIENT_ID is set in Vercel

### **Ngrok tunnel expired:**
- Free ngrok tunnels expire after 2 hours
- Restart ngrok: `ngrok http 8000`
- Update the new URL in Vercel environment variables
- Redeploy frontend

---

## 📊 Current System Status

```
✅ Backend: Running on Mac (localhost:8000)
✅ Ngrok: Active (https://c2cf-115-244-141-202.ngrok-free.app)
✅ Frontend: Deployed on Vercel (https://aegis-frontend-sigma.vercel.app)
✅ GitHub OAuth: Configured
✅ Database: SQLite on Mac
✅ Docker Sandbox: Running on Mac
✅ 4-Agent System: Ready
```

---

## 🎯 Quick Commands

### **Check Backend Status:**
```bash
curl https://c2cf-115-244-141-202.ngrok-free.app/health
```

### **Check Ngrok Status:**
```bash
curl http://localhost:4040/api/tunnels
```

### **Restart Backend:**
```bash
cd Aegis
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### **Restart Ngrok:**
```bash
ngrok http 8000
```

---

## ✅ Deployment Checklist

- [ ] Backend running on Mac (port 8000)
- [ ] Ngrok tunnel active and URL noted
- [ ] Environment variables added in Vercel
- [ ] Frontend redeployed on Vercel
- [ ] GitHub OAuth callback URL updated
- [ ] Tested login flow
- [ ] Tested repository addition
- [ ] Mac set to never sleep

---

**Last Updated**: April 25, 2026  
**Ngrok URL**: https://c2cf-115-244-141-202.ngrok-free.app  
**Frontend URL**: https://aegis-frontend-sigma.vercel.app
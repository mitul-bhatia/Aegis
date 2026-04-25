# 🎯 Aegis Deployment - READY TO GO!

**Date**: April 25, 2026  
**Status**: ✅ All Systems Operational

---

## 🟢 Current System Status

### **Backend (Mac Local)**
- **Status**: ✅ Running
- **Local URL**: http://localhost:8000
- **Ngrok Tunnel**: https://c2cf-115-244-141-202.ngrok-free.app
- **Health Check**: ✅ Responding
- **Process**: Running in background (Terminal ID: 12)

### **Ngrok Tunnel**
- **Status**: ✅ Active
- **Public URL**: https://c2cf-115-244-141-202.ngrok-free.app
- **Process**: Running in background (Terminal ID: 13)
- **Web Interface**: http://localhost:4040

### **Frontend (Vercel)**
- **Deployment URL**: https://aegis-frontend-sigma.vercel.app
- **Status**: Ready for deployment
- **Process**: Running locally on port 3000 (Terminal ID: 9)

---

## 📝 What to Do in Vercel

### **Step 1: Add Environment Variables**

Go to: https://vercel.com/mitul-bhatias-projects/aegis-frontend/settings/environment-variables

Add these **TWO** environment variables:

#### **Variable 1:**
```
Key:   NEXT_PUBLIC_API_URL
Value: https://c2cf-115-244-141-202.ngrok-free.app
```
- Select: ✅ Production
- Select: ✅ Preview
- Click: **Save**

#### **Variable 2:**
```
Key:   NEXT_PUBLIC_GITHUB_CLIENT_ID
Value: Ov23li7vdknIS2ZtxxOH
```
- Select: ✅ Production
- Select: ✅ Preview
- Click: **Save**

---

### **Step 2: Configure Build Settings**

In the **Build & Development Settings** section (from your screenshot):

#### **Root Directory:**
```
aegis-frontend
```

#### **Build Command:**
Leave as default (Next.js will auto-detect)

#### **Output Directory:**
Leave as default (`.next`)

#### **Install Command:**
Leave as default (`npm install`)

---

### **Step 3: Deploy**

After adding environment variables:

1. Go to **Deployments** tab
2. Click **Redeploy** on the latest deployment
3. Wait for deployment to complete (~2-3 minutes)
4. Visit: https://aegis-frontend-sigma.vercel.app

---

## ✅ GitHub OAuth Already Configured

Your GitHub OAuth app is correctly set up:

- **Application name**: aegis
- **Homepage URL**: https://aegis-frontend-sigma.vercel.app ✅
- **Callback URL**: https://aegis-frontend-sigma.vercel.app/auth/callback ✅
- **Client ID**: Ov23li7vdknIS2ZtxxOH ✅
- **Client Secret**: Configured in backend ✅

**No changes needed!**

---

## 🧪 Testing After Deployment

### **1. Test Frontend Access**
```
Visit: https://aegis-frontend-sigma.vercel.app
Expected: Dashboard loads
```

### **2. Test Backend Connection**
```bash
curl https://c2cf-115-244-141-202.ngrok-free.app/health
Expected: {"status":"Aegis is running","version":"0.1.0"}
```

### **3. Test GitHub OAuth**
```
1. Click "Sign in with GitHub" on frontend
2. Authorize the app
3. Should redirect back to dashboard
4. Should see your repositories
```

### **4. Test Full Pipeline**
```
1. Add repository: mitu1046/aegis-test-repo
2. Push vulnerable code to the repo
3. Watch real-time updates in dashboard
4. Verify PR is created automatically
```

---

## ⚠️ IMPORTANT: Keep Mac Running

### **What's Running on Your Mac:**
- ✅ Backend server (port 8000)
- ✅ Ngrok tunnel (exposing backend)
- ✅ Docker daemon (for exploit sandbox)
- ✅ SQLite database
- ✅ ChromaDB vector database

### **Keep These Running:**
```bash
# Check backend status
curl http://localhost:8000/health

# Check ngrok status
curl http://localhost:4040/api/tunnels

# View backend logs
# (Terminal ID: 12)

# View ngrok logs
# (Terminal ID: 13)
```

### **Mac Settings:**
- ⚠️ **Disable sleep mode**
- ⚠️ **Keep Mac plugged in**
- ⚠️ **Don't close terminal windows**

---

## 🔄 If Ngrok URL Changes

If you restart ngrok and get a new URL:

### **1. Get New URL:**
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['tunnels'][0]['public_url'])"
```

### **2. Update Vercel:**
- Go to Environment Variables
- Update `NEXT_PUBLIC_API_URL` with new URL
- Redeploy frontend

### **3. Update Backend:**
- Update `BACKEND_URL` in `Aegis/.env`
- Restart backend server

---

## 📊 System Architecture

```
User Browser
    ↓
Vercel Frontend (https://aegis-frontend-sigma.vercel.app)
    ↓
Ngrok Tunnel (https://c2cf-115-244-141-202.ngrok-free.app)
    ↓
Mac Backend (localhost:8000)
    ↓
├─ 4-Agent System (Finder, Exploiter, Engineer, Verifier)
├─ Docker Sandbox (Exploit testing)
├─ SQLite Database (Scan records)
├─ ChromaDB (RAG context)
└─ GitHub API (Webhooks, PRs)
```

---

## 🎯 Quick Reference

### **URLs:**
- **Frontend**: https://aegis-frontend-sigma.vercel.app
- **Backend (Ngrok)**: https://c2cf-115-244-141-202.ngrok-free.app
- **Backend (Local)**: http://localhost:8000
- **Ngrok Dashboard**: http://localhost:4040

### **Environment Variables for Vercel:**
```
NEXT_PUBLIC_API_URL=https://c2cf-115-244-141-202.ngrok-free.app
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23li7vdknIS2ZtxxOH
```

### **GitHub OAuth:**
```
Client ID: Ov23li7vdknIS2ZtxxOH
Client Secret: 0a7a157122949acf0c24f21ca38b148db8e12108
Callback: https://aegis-frontend-sigma.vercel.app/auth/callback
```

---

## ✅ Deployment Checklist

- [x] Backend running on Mac (port 8000)
- [x] Ngrok tunnel active
- [x] Frontend code ready
- [x] Environment variables documented
- [x] GitHub OAuth configured
- [ ] Add environment variables in Vercel
- [ ] Deploy frontend on Vercel
- [ ] Test login flow
- [ ] Test repository addition
- [ ] Test vulnerability detection

---

**Ready to deploy! Just add the environment variables in Vercel and redeploy.** 🚀

**Last Updated**: April 25, 2026  
**Ngrok URL**: https://c2cf-115-244-141-202.ngrok-free.app
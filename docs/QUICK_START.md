# 🚀 Aegis Quick Start Guide

Get Aegis running in 5 minutes!

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** (for sandbox isolation)
- **GitHub account**

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/aegis.git
cd aegis
```

---

## Step 2: Setup Backend

### 2.1 Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Install Semgrep

```bash
# macOS (Homebrew)
brew install semgrep

# Linux (pip)
pip install semgrep

# Or use Docker (automatic fallback)
```

### 2.4 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required: AI Models
MISTRAL_API_KEY=your_mistral_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# Required: GitHub Integration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Optional: GitHub OAuth (for multi-user)
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret

# Server
PORT=8000
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### 2.5 Build Docker Sandbox

```bash
bash build-sandbox.sh
```

This creates the `aegis-sandbox:latest` image for secure exploit testing.

### 2.6 Start Backend

```bash
python main.py
```

Backend will be available at `http://localhost:8000`

---

## Step 3: Setup Frontend

### 3.1 Install Dependencies

```bash
cd aegis-frontend
npm install
```

### 3.2 Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3.3 Start Frontend

```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## Step 4: Configure GitHub Webhook

### 4.1 Create Webhook

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `http://your-server:8000/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Same as `GITHUB_WEBHOOK_SECRET` in `.env`
   - **Events**: Select "Push events" and "Pull requests"
4. Click **Add webhook**

### 4.2 Test Webhook (Optional)

Use ngrok for local testing:

```bash
ngrok http 8000
```

Update webhook URL to ngrok URL (e.g., `https://abc123.ngrok.io/webhook/github`)

---

## Step 5: Add Your First Repository

### 5.1 Open Dashboard

Navigate to `http://localhost:3000/dashboard`

### 5.2 Add Repository

1. Click **Add Repository**
2. Enter repository URL (e.g., `https://github.com/owner/repo`)
3. Click **Add**

Aegis will:
- Install webhook automatically
- Index the repository (RAG)
- Start monitoring for vulnerabilities

---

## Step 6: Trigger Your First Scan

### Option A: Push Code

Make a commit to your repository:

```bash
git add .
git commit -m "Test commit"
git push
```

Aegis will automatically:
1. Receive webhook event
2. Run Semgrep scan
3. Identify vulnerabilities
4. Write exploits
5. Test in Docker sandbox
6. Generate patches
7. Create PR

### Option B: Manual Trigger

Use the dashboard:

1. Go to **Repositories**
2. Click **Trigger Scan** on your repo
3. Watch real-time progress

---

## Step 7: View Results

### Dashboard View

Navigate to `http://localhost:3000/dashboard` to see:

- **Real-time scan progress** with SSE updates
- **Vulnerability cards** with severity badges
- **Exploit output** in terminal view
- **Patch diffs** side-by-side
- **PR links** to GitHub

### Scan Details

Click on any scan to see:

- Original vulnerable code
- Exploit script
- Exploit output (proof)
- Patched code
- Unit tests
- Verification results

---

## Demo Mode (Optional)

For testing without real vulnerabilities:

```bash
# In .env
DEMO_MODE=true
```

Demo mode simulates:
- Vulnerabilities found
- Exploits succeed
- Patches generated
- Tests pass
- PRs created

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check logs
tail -f aegis.log
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache
rm -rf .next node_modules
npm install
npm run dev
```

### Docker sandbox not working

```bash
# Check Docker is running
docker ps

# Rebuild sandbox
bash build-sandbox.sh

# Check image exists
docker images | grep aegis-sandbox
```

### Webhook not receiving events

```bash
# Check webhook secret matches
echo $GITHUB_WEBHOOK_SECRET

# Check webhook URL is accessible
curl -X POST http://your-server:8000/webhook/github

# Use ngrok for local testing
ngrok http 8000
```

### Semgrep not found

```bash
# Install Semgrep
brew install semgrep  # macOS
pip install semgrep   # Linux

# Or set path in .env
SEMGREP_BIN=/path/to/semgrep
```

---

## Next Steps

- **[Configuration Guide](CONFIGURATION.md)** - Customize Aegis settings
- **[Architecture Guide](ARCHITECTURE.md)** - Understand the system
- **[API Reference](API_REFERENCE.md)** - Build integrations
- **[Development Guide](DEVELOPMENT.md)** - Contribute to Aegis

---

## Quick Commands

```bash
# Start backend
python main.py

# Start frontend
cd aegis-frontend && npm run dev

# Build sandbox
bash build-sandbox.sh

# Run tests
pytest

# Check logs
tail -f aegis.log

# Stop all
pkill -f "python main.py"
pkill -f "next dev"
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/aegis/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/aegis/discussions)
- **Email**: support@aegis-security.dev

---

**Congratulations! 🎉 Aegis is now running and monitoring your repositories for vulnerabilities.**

---

**Last Updated**: April 25, 2026  
**Status**: 🟢 Production Ready

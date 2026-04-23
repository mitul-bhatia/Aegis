# 🔧 Fix GitHub Token Permissions

## ❌ **THE PROBLEM**

Your current GitHub token has **NO SCOPES** - it can't install webhooks!

```
Current token scopes: (empty)
Required scopes: repo, admin:repo_hook
```

---

## ✅ **THE SOLUTION**

Create a new GitHub Personal Access Token with the correct permissions.

### Step 1: Go to GitHub Settings
🔗 https://github.com/settings/tokens

### Step 2: Generate New Token
1. Click **"Generate new token"**
2. Select **"Generate new token (classic)"** (NOT fine-grained)

### Step 3: Configure Token
- **Note:** `Aegis Webhook Manager`
- **Expiration:** Choose your preference (90 days recommended)

### Step 4: Select Scopes
Check these boxes:
- ✅ **`repo`** - Full control of private repositories
  - This includes: repo:status, repo_deployment, public_repo, repo:invite, security_events
- ✅ **`admin:repo_hook`** - Full control of repository hooks
  - This includes: write:repo_hook, read:repo_hook

### Step 5: Generate Token
1. Scroll down
2. Click **"Generate token"**
3. **COPY THE TOKEN** (starts with `ghp_`)
   - ⚠️ You won't see it again!

### Step 6: Update .env File
```bash
# Open .env file
nano .env

# Replace the GITHUB_TOKEN line with:
GITHUB_TOKEN=ghp_YOUR_NEW_TOKEN_HERE

# Save and exit (Ctrl+X, then Y, then Enter)
```

### Step 7: Restart Backend
```bash
./start-backend.sh
```

### Step 8: Verify
```bash
source .venv/bin/activate
python test-github-token.py
```

Should show:
```
✅ repo
✅ admin:repo_hook
✅ All required permissions are present!
```

---

## 🎯 **Why This Happened**

You're using a **fine-grained token** (`github_pat_...`) which has very limited permissions by default.

Aegis needs a **classic token** (`ghp_...`) with full `repo` and `admin:repo_hook` scopes.

---

## 📝 **Token Types Comparison**

| Type | Prefix | Scopes | Use Case |
|------|--------|--------|----------|
| Classic | `ghp_` | Full control | ✅ Aegis (webhooks) |
| Fine-grained | `github_pat_` | Limited | ❌ Not enough for webhooks |

---

## 🔐 **Security Note**

The token needs these permissions to:
- **`repo`** - Read repository code and metadata
- **`admin:repo_hook`** - Install/manage webhooks

This is standard for CI/CD tools and security scanners.

---

## ⚡ **Quick Commands**

```bash
# Test current token
python test-github-token.py

# List accessible repos
python list-my-repos.py

# Restart backend after updating token
./start-backend.sh

# Test complete system
python test-complete-system.py
```

---

## 🐛 **Still Having Issues?**

1. Make sure you selected **"classic"** token, not fine-grained
2. Verify both `repo` and `admin:repo_hook` are checked
3. Copy the ENTIRE token (they're long!)
4. No spaces before/after the token in `.env`
5. Restart the backend after updating

---

**Once you update the token, everything will work! 🚀**

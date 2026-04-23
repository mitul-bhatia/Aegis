# 🧪 Aegis Testing Plan

**Complete testing strategy for end-to-end verification**

---

## 📋 Testing Checklist

### Phase 1: Component Tests ✅
- [x] Semgrep scanner
- [x] RAG indexer/retriever
- [x] Agent 1 (Finder)
- [x] Agent 2 (Exploiter)
- [x] Agent 3 (Engineer)
- [x] Agent 4 (Verifier)
- [x] Docker sandbox
- [x] 4-agent pipeline integration

### Phase 2: API Tests (Now)
- [ ] Backend health check
- [ ] SSE endpoint streaming
- [ ] Repos API
- [ ] Scans API
- [ ] Webhook signature verification

### Phase 3: Real GitHub Push Test (Now)
- [ ] Push vulnerable code to test repo
- [ ] Webhook triggers pipeline
- [ ] Watch real-time status updates
- [ ] Verify PR creation
- [ ] Check RAG update

### Phase 4: Frontend Tests (Browser Required)
- [ ] Dashboard loads
- [ ] SSE connection established
- [ ] Real-time scan updates
- [ ] VulnCard collapsible sections
- [ ] AddRepoModal progress states
- [ ] Status badges animate correctly

---

## 🎯 Test Repository

**URL**: https://github.com/mitu1046/aegis-test-repo  
**Status**: Already configured in database  
**Webhook ID**: 609148813  
**Is Indexed**: Yes

---

## 🧪 Test Scenarios

### Scenario 1: SQL Injection
**File**: `app.py`  
**Vulnerability**: String concatenation in SQL query  
**Expected**: Finder identifies, Exploiter confirms, Engineer patches, Verifier approves

### Scenario 2: Command Injection
**File**: `utils.py`  
**Vulnerability**: Unsanitized user input in subprocess  
**Expected**: Finder identifies, Exploiter confirms, Engineer patches, Verifier approves

### Scenario 3: Path Traversal
**File**: `file_handler.py`  
**Vulnerability**: Unsanitized file path  
**Expected**: Finder identifies, Exploiter confirms, Engineer patches, Verifier approves

---

## 📝 Test Execution Steps

### Step 1: Verify Backend is Running
```bash
curl http://localhost:8000/api/scans
# Should return JSON with scans
```

### Step 2: Verify SSE Endpoint
```bash
curl -N -m 10 http://localhost:8000/api/scans/live
# Should stream: data: {...}
```

### Step 3: Check Test Repo Status
```bash
sqlite3 aegis.db "SELECT * FROM repos WHERE full_name='mitu1046/aegis-test-repo';"
# Should show: is_indexed=1, status=monitoring
```

### Step 4: Push Vulnerable Code
```bash
# Clone test repo
git clone https://github.com/mitu1046/aegis-test-repo.git
cd aegis-test-repo

# Create vulnerable file
cat > app.py << 'EOF'
import sqlite3

def get_user(username):
    """Vulnerable to SQL injection"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: String concatenation
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

if __name__ == "__main__":
    print(get_user("admin"))
EOF

# Commit and push
git add app.py
git commit -m "Add user lookup function"
git push origin main
```

### Step 5: Watch Pipeline Execution
```bash
# Terminal 1: Watch backend logs
tail -f logs/aegis.log

# Terminal 2: Watch SSE stream
curl -N http://localhost:8000/api/scans/live

# Terminal 3: Watch database
watch -n 2 'sqlite3 aegis.db "SELECT id, status, vulnerability_type FROM scans ORDER BY created_at DESC LIMIT 1;"'
```

### Step 6: Verify Results
```bash
# Check final scan status
sqlite3 aegis.db "SELECT * FROM scans ORDER BY created_at DESC LIMIT 1;"

# Should show:
# - status: fixed
# - vulnerability_type: SQL Injection
# - pr_url: https://github.com/mitu1046/aegis-test-repo/pull/X
```

---

## 🌐 Frontend Testing (Browser Required)

### Step 1: Open Dashboard
1. Open browser to http://localhost:3000/dashboard
2. Should see 2 repos listed
3. Should see existing scans

### Step 2: Watch Real-time Updates
1. Keep dashboard open
2. Push vulnerable code (Step 4 above)
3. Watch for new scan card to appear
4. Watch status badge change:
   - queued → scanning → exploiting → patching → verifying → fixed

### Step 3: Test VulnCard Features
1. Click on scan card
2. Expand "Exploit Output" section
3. Expand "Patch Diff" section
4. Click "View PR" button
5. Verify PR opens in GitHub

### Step 4: Test AddRepoModal
1. Click "Monitor Repo" button
2. Enter: `github.com/test-user/another-repo`
3. Click "Start Monitoring"
4. Watch progress steps:
   - Validating (spinner → checkmark)
   - Installing webhook (spinner → checkmark)
   - Indexing codebase (spinner → checkmark)
5. Success message appears
6. Modal auto-closes
7. New repo appears in list

---

## 🐛 Known Issues to Test

### Issue 1: Semgrep Python 3.14 Incompatibility
**Status**: Fixed (Docker fallback)  
**Test**: Run semgrep scan, should use Docker

### Issue 2: RAG Update Timing
**Status**: Fixed (non-fatal)  
**Test**: Verify RAG updates after patch

### Issue 3: SSE Connection Drops
**Status**: Should be stable  
**Test**: Keep dashboard open for 5+ minutes

---

## 📊 Success Criteria

### Backend
- ✅ All API endpoints respond
- ✅ SSE streams data
- ✅ Webhook receives push events
- ✅ 4-agent pipeline completes
- ✅ PR is created
- ✅ RAG is updated

### Frontend
- ✅ Dashboard loads
- ✅ SSE connection established
- ✅ Real-time updates work
- ✅ VulnCard sections expand/collapse
- ✅ Status badges animate
- ✅ PR links work

### Integration
- ✅ GitHub push triggers pipeline
- ✅ Status updates in real-time
- ✅ PR contains exploit proof + patch
- ✅ Tests are generated
- ✅ Exploit is blocked by patch

---

## 🚨 Troubleshooting

### Backend Not Responding
```bash
# Check if running
ps aux | grep uvicorn

# Restart
./start-backend.sh
```

### Frontend Not Loading
```bash
# Check if running
ps aux | grep next

# Restart
cd aegis-frontend
npm run dev
```

### Webhook Not Triggering
```bash
# Check webhook in GitHub
# Settings → Webhooks → Check recent deliveries

# Verify webhook secret matches .env
grep GITHUB_WEBHOOK_SECRET .env
```

### SSE Not Streaming
```bash
# Test directly
curl -N -m 10 http://localhost:8000/api/scans/live

# Check CORS settings in main.py
```

---

## 📝 Test Results Template

```markdown
## Test Results - [Date]

### Backend Tests
- [ ] API endpoints: PASS/FAIL
- [ ] SSE streaming: PASS/FAIL
- [ ] Webhook: PASS/FAIL
- [ ] 4-agent pipeline: PASS/FAIL
- [ ] PR creation: PASS/FAIL

### Frontend Tests
- [ ] Dashboard: PASS/FAIL
- [ ] SSE connection: PASS/FAIL
- [ ] Real-time updates: PASS/FAIL
- [ ] VulnCard: PASS/FAIL
- [ ] AddRepoModal: PASS/FAIL

### Integration Tests
- [ ] GitHub push: PASS/FAIL
- [ ] Status updates: PASS/FAIL
- [ ] PR quality: PASS/FAIL
- [ ] RAG update: PASS/FAIL

### Issues Found
1. [Issue description]
2. [Issue description]

### Notes
[Any additional observations]
```

---

**Testing Status**: Ready to Execute  
**Next**: Run automated tests, then manual GitHub push test

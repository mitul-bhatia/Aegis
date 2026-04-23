# 🌐 Browser Testing Guide for Aegis

**Step-by-step instructions for testing Aegis in the browser**

---

## ✅ Prerequisites

Before starting, ensure:
- ✅ Backend is running on http://localhost:8000
- ✅ Frontend is running on http://localhost:3000
- ✅ All system tests passed (`python test-complete-system.py`)
- ✅ Test repo is configured: https://github.com/mitu1046/aegis-test-repo

---

## 📋 Testing Checklist

### Part 1: Dashboard Initial State
- [ ] Dashboard loads without errors
- [ ] 2 repos are visible
- [ ] Existing scans are displayed
- [ ] SSE connection established (check DevTools)

### Part 2: Real-time Updates
- [ ] Push vulnerable code to test repo
- [ ] New scan appears in dashboard
- [ ] Status badge updates in real-time
- [ ] All status transitions visible

### Part 3: VulnCard Features
- [ ] Exploit Output section expands/collapses
- [ ] Patch Diff section expands/collapses
- [ ] PR button appears when PR is created
- [ ] PR link opens correctly

### Part 4: AddRepoModal (Optional)
- [ ] Modal opens when clicking "Monitor Repo"
- [ ] Progress steps animate correctly
- [ ] Modal auto-closes on success
- [ ] New repo appears in list

---

## 🚀 Step-by-Step Testing

### Step 1: Open Dashboard

1. **Open browser** (Chrome, Firefox, or Safari)
2. **Navigate to**: http://localhost:3000/dashboard
3. **Expected**: Dashboard loads with:
   - Header showing "Aegis" logo
   - "Monitored Repositories" section with 2 repos
   - "Scan Feed" section with existing scans

**Screenshot checkpoint**: Dashboard loaded

---

### Step 2: Check SSE Connection

1. **Open DevTools** (F12 or Cmd+Option+I)
2. **Go to Network tab**
3. **Filter by**: EventSource or "scans/live"
4. **Expected**: You should see:
   - Connection to `/api/scans/live`
   - Status: "pending" (streaming)
   - Type: "eventsource"

**Screenshot checkpoint**: SSE connection in DevTools

---

### Step 3: Prepare to Push Vulnerable Code

**Keep the dashboard open in your browser!**

Now, in a terminal, we'll push vulnerable code to trigger the pipeline.

---

### Step 4: Push Vulnerable Code (Terminal)

Open a **new terminal** and run:

```bash
# Navigate to a temporary directory
cd /tmp

# Clone the test repo
git clone https://github.com/mitu1046/aegis-test-repo.git
cd aegis-test-repo

# Copy vulnerable file
cat > app.py << 'EOF'
"""
Vulnerable SQL Injection Example
"""
import sqlite3

def get_user(username):
    """Fetch user by username - VULNERABLE"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: String concatenation in SQL query
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

**Expected**: Push succeeds, webhook triggers

---

### Step 5: Watch Dashboard for Real-time Updates

**Switch back to your browser with the dashboard open**

You should see:

1. **New scan card appears** (within 5-10 seconds)
   - Shows commit SHA (first 8 chars)
   - Shows branch name
   - Status badge: "Queued" or "Scanning"

2. **Status badge updates** (watch it change):
   - 🔵 Queued (pulse animation)
   - 🔍 Scanning (spinning icon)
   - ⚡ Exploiting (spinning icon)
   - 🚨 Exploit Found (red badge)
   - 🔧 Patching (spinning icon)
   - 🛡️ Verifying (spinning icon)
   - ✅ Fixed (green badge)

3. **Vulnerability details appear**:
   - Type: "SQL Injection"
   - Severity: "CRITICAL" or "ERROR"
   - File: "app.py"

**Screenshot checkpoint**: Scan card with "Fixed" status

---

### Step 6: Test VulnCard Collapsible Sections

1. **Find the scan card** with "SQL Injection"

2. **Click "Exploit Output"** section
   - **Expected**: Section expands
   - **Shows**: Python exploit code output
   - **Contains**: "VULNERABLE" message

3. **Click "Exploit Output"** again
   - **Expected**: Section collapses

4. **Click "Patch Diff"** section
   - **Expected**: Section expands
   - **Shows**: Code diff with - and + lines
   - **Contains**: Parameterized query fix

5. **Click "Patch Diff"** again
   - **Expected**: Section collapses

**Screenshot checkpoint**: Expanded sections

---

### Step 7: Test PR Button

1. **Look for "View PR" button** on the scan card
   - **Expected**: Button appears after status is "Fixed"

2. **Click "View PR" button**
   - **Expected**: New tab opens
   - **Opens**: GitHub PR page
   - **URL**: https://github.com/mitu1046/aegis-test-repo/pull/X

3. **Check PR contents**:
   - Title mentions vulnerability type
   - Description includes:
     - Vulnerability explanation
     - Exploit proof
     - Patch explanation
   - Files changed shows the fix

**Screenshot checkpoint**: GitHub PR page

---

### Step 8: Verify Status Badge Animations

Watch the status badges during the pipeline:

1. **Queued** - Should pulse (fade in/out)
2. **Scanning** - Icon should spin
3. **Exploiting** - Icon should spin
4. **Patching** - Icon should spin
5. **Verifying** - Icon should spin
6. **Fixed** - Static green checkmark

**Screenshot checkpoint**: Different status badges

---

### Step 9: Test AddRepoModal (Optional)

1. **Click "Monitor Repo" button** (top right)
   - **Expected**: Modal opens

2. **Enter repo URL**: `github.com/test-user/another-repo`
   - **Note**: This will fail (repo doesn't exist), but tests the UI

3. **Click "Start Monitoring"**
   - **Expected**: Progress steps appear:
     - ✓ Validating repository
     - ⏳ Installing webhook (will fail)

4. **Check error message**
   - **Expected**: Error message appears
   - **Message**: Something like "Repository not found"

5. **Close modal**

**Screenshot checkpoint**: AddRepoModal with progress

---

### Step 10: Check Console for Errors

1. **Open DevTools Console** (if not already open)
2. **Look for errors** (red text)
3. **Expected**: No critical errors
   - Some warnings are OK
   - SSE connection errors during page load are OK

**Screenshot checkpoint**: Clean console (or minor warnings only)

---

## 📊 Expected Timeline

From push to PR creation:

- **0:00** - Push code
- **0:05** - Webhook received, scan created
- **0:10** - Semgrep scan complete
- **0:20** - Finder identifies vulnerability
- **0:35** - Exploiter generates exploit
- **0:40** - Docker tests exploit (confirmed)
- **0:55** - Engineer generates patch + tests
- **1:05** - Verifier tests patch
- **1:10** - RAG updated
- **1:15** - PR created
- **1:20** - Status: Fixed

**Total time**: ~1-2 minutes

---

## 🐛 Troubleshooting

### Issue: Dashboard doesn't load
**Solution**: 
```bash
cd aegis-frontend
npm run dev
```

### Issue: No new scan appears
**Solution**:
1. Check backend logs: `tail -f logs/aegis.log`
2. Check webhook delivery in GitHub:
   - Go to repo Settings → Webhooks
   - Click on webhook
   - Check "Recent Deliveries"

### Issue: SSE connection fails
**Solution**:
1. Check DevTools Network tab
2. Look for CORS errors
3. Restart backend if needed

### Issue: Status stuck on "Scanning"
**Solution**:
1. Check backend logs for errors
2. Check database: `sqlite3 aegis.db "SELECT * FROM scans ORDER BY created_at DESC LIMIT 1;"`
3. Pipeline may have crashed - check logs

---

## ✅ Success Criteria

You've successfully tested Aegis if:

- ✅ Dashboard loads and displays repos/scans
- ✅ SSE connection established
- ✅ New scan appears after push
- ✅ Status updates in real-time
- ✅ All status transitions visible
- ✅ Collapsible sections work
- ✅ PR is created and link works
- ✅ No critical console errors

---

## 📸 Screenshots to Take

1. Dashboard initial state
2. SSE connection in DevTools
3. Scan card with "Scanning" status
4. Scan card with "Exploiting" status
5. Scan card with "Fixed" status
6. Expanded "Exploit Output" section
7. Expanded "Patch Diff" section
8. GitHub PR page
9. DevTools console (clean)

---

## 🎥 Optional: Record Video

For demo purposes, consider recording:

1. **Screen recording** of the entire process
2. **Start**: Dashboard with existing scans
3. **Show**: Push command in terminal
4. **Show**: Real-time status updates
5. **Show**: Collapsible sections
6. **End**: GitHub PR page

**Tools**: QuickTime (Mac), OBS Studio (cross-platform)

---

## 📝 Test Results Template

```markdown
## Browser Test Results - [Date]

### Dashboard
- [ ] Loads correctly
- [ ] Shows 2 repos
- [ ] Shows existing scans
- [ ] SSE connection established

### Real-time Updates
- [ ] New scan appears
- [ ] Status updates in real-time
- [ ] All transitions visible
- [ ] Timeline: ~X minutes

### VulnCard
- [ ] Exploit Output expands/collapses
- [ ] Patch Diff expands/collapses
- [ ] PR button appears
- [ ] PR link works

### Console
- [ ] No critical errors
- [ ] Warnings (if any): [list]

### Screenshots
- [ ] All 9 screenshots taken
- [ ] Stored in: [location]

### Issues Found
1. [Issue description]
2. [Issue description]

### Notes
[Any additional observations]
```

---

**Testing Status**: Ready to Execute  
**Estimated Time**: 15-20 minutes  
**Next**: Follow steps above and document results

---

## 🚀 Quick Start (TL;DR)

1. Open http://localhost:3000/dashboard
2. Open DevTools (F12) → Network tab
3. Push vulnerable code (see Step 4)
4. Watch status updates in real-time
5. Click collapsible sections
6. Click "View PR" button
7. Take screenshots
8. Done! 🎉

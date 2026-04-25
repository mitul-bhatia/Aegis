# Phase 7 — Feature Expansion

> **Depends on:** Phases 1-6 complete (foundation is solid)
>
> **Estimated effort:** Ongoing
>
> **Goal:** Add new capabilities that make Aegis a complete security platform — PR review mode, dependency scanning, notifications, and advanced analytics.

---

## Task 7.1: PR-Targeted Scanning

**Files:** `orchestrator.py` / `pipeline/graph.py`, `main.py`

**Current state:** PR scanning partially works but uses the same full-repo pipeline. Should be diff-only.

**Steps:**
- [ ] Detect `push_info["is_pr"]` and switch to PR-specific flow:
  - Only scan the PR diff (not the full codebase)
  - Fetch changed files from PR API: `GET /repos/{owner}/{repo}/pulls/{pr_number}/files`
  - Instead of creating a new PR, add a review comment to the existing PR
- [ ] Post findings as PR review comments on specific lines:
  ```python
  pr.create_review(
      body="Aegis found a vulnerability",
      event="COMMENT",
      comments=[{
          "path": "app.py",
          "position": 12,
          "body": "🛡️ **SQL Injection** detected...\n\n```diff\n-query = f\"SELECT ...\"\n+query = \"SELECT ... WHERE id = %s\"\n```"
      }]
  )
  ```
- [ ] Add inline fix suggestions using GitHub's suggestion feature:
  ```markdown
  ````suggestion
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
  ````
  ```

**Verification:**
- Open a PR with vulnerable code → Aegis posts inline comments on the PR
- Comments include specific fix suggestions
- No duplicate PR is created

---

## Task 7.2: Dependency Vulnerability Scanning

**Files:** NEW `scanner/dependency_scanner.py`, `pipeline/nodes.py`

**Steps:**
- [ ] Parse dependency files: `requirements.txt`, `package.json`, `Gemfile`, `go.mod`
- [ ] Query the OSV (Open Source Vulnerabilities) API for known CVEs:
  ```python
  import requests
  
  def scan_dependencies(repo_path: str) -> list[dict]:
      vulns = []
      
      # Python
      requirements = os.path.join(repo_path, "requirements.txt")
      if os.path.exists(requirements):
          with open(requirements) as f:
              for line in f:
                  pkg, version = parse_requirement(line)
                  if version:
                      osv_result = query_osv(f"PyPI/{pkg}", version)
                      if osv_result:
                          vulns.append({
                              "source": "requirements.txt",
                              "package": pkg,
                              "version": version,
                              "cves": osv_result
                          })
      
      # Node
      package_json = os.path.join(repo_path, "package.json")
      if os.path.exists(package_json):
          ...
      
      return vulns
  
  def query_osv(ecosystem_package: str, version: str) -> list:
      """Query OSV.dev for known vulnerabilities."""
      response = requests.post(
          "https://api.osv.dev/v1/query",
          json={"package": {"name": ecosystem_package.split("/")[1], "ecosystem": ecosystem_package.split("/")[0]}, "version": version},
          timeout=10
      )
      if response.ok:
          return response.json().get("vulns", [])
      return []
  ```

- [ ] Add dependency scanning as a parallel node in the LangGraph pipeline
- [ ] Create separate scan results section in the frontend for dependency vulns
- [ ] Generate separate PRs or comments for dependency updates

**Verification:**
- Repo with an old `flask==1.0` → dependency scanner flags known CVEs
- Frontend shows "2 dependency vulnerabilities found"
- Can be filtered/dismissed separately from code vulns

---

## Task 7.3: Slack/Discord Notifications

**Files:** NEW `notifications/`, `config.py`, `.env`

**Steps:**
- [ ] Create notification abstraction:
  ```python
  class NotificationChannel:
      async def send(self, title: str, body: str, severity: str, scan_url: str): ...
  
  class SlackNotifier(NotificationChannel):
      def __init__(self, webhook_url: str):
          self.webhook_url = webhook_url
      
      async def send(self, title, body, severity, scan_url):
          color = {"CRITICAL": "#ff0000", "HIGH": "#ff6600", ...}[severity]
          requests.post(self.webhook_url, json={
              "attachments": [{
                  "color": color,
                  "title": title,
                  "text": body,
                  "actions": [{"type": "button", "text": "View in Aegis", "url": scan_url}]
              }]
          })
  
  class DiscordNotifier(NotificationChannel):
      ...
  ```
- [ ] Add `SLACK_WEBHOOK_URL` and `DISCORD_WEBHOOK_URL` to config
- [ ] Trigger notification when scan reaches terminal state:
  - FIXED → "🛡️ Vulnerability patched in repo/name"
  - FAILED → "❌ Scan failed for repo/name — human review needed"
  - EXPLOIT_CONFIRMED → "🚨 Exploitable vulnerability found in repo/name"

**Verification:**
- Add Slack webhook → vulnerability found → message appears in Slack
- Notifications include direct link to scan detail page

---

## Task 7.4: Regression Detection

**Files:** `pipeline/nodes.py`, `orchestrator.py`

**Steps:**
- [ ] Track which vulnerability types have been fixed in each file
- [ ] After a successful fix, store the "vulnerability signature":
  ```python
  class VulnSignature:
      repo_id: int
      file_path: str
      vuln_type: str
      fixed_at: datetime
      fix_commit: str
  ```
- [ ] When the same file is modified in a future commit, check if:
  - The fix was reverted (diff undoes the patch)
  - The same vulnerability pattern reappears
- [ ] If regression detected: flag as `REGRESSION` priority level (higher than CRITICAL)

**Verification:**
- Fix SQL injection in `app.py` → push new commit that reverts the fix → flagged as regression
- Dashboard shows "Regression" badge with link to original fix

---

## Task 7.5: Multi-Language Support

**Files:** `config.py`, `scanner/semgrep_runner.py`, `agents/finder.py`

**Steps:**
- [ ] Expand `CODE_EXTENSIONS` to include C/C++, Rust, Kotlin, Swift
- [ ] Add language-specific Semgrep rulesets:
  ```python
  LANGUAGE_RULESETS = {
      ".py": "p/python",
      ".js": "p/javascript",
      ".ts": "p/typescript",
      ".java": "p/java",
      ".go": "p/golang",
      ".rb": "p/ruby",
      ".php": "p/php",
      ".rs": "p/rust",
  }
  ```
- [ ] Update Finder prompt with language-specific vulnerability patterns
- [ ] Add language detection to Triage agent

**Verification:**
- Push a Java file with SQL injection → Aegis detects and patches it
- Push a Go file with path traversal → Aegis handles it

---

## Task 7.6: Security Dashboard Analytics

**Files:** NEW `app/analytics/page.tsx`, backend analytics endpoint

**Steps:**
- [ ] Create an analytics page with:
  - Vulnerability trend chart (vulns found over time)
  - Fix rate chart (% of vulns fixed within 24h)
  - Top vulnerability types pie chart
  - Mean time to remediation (MTTR) metric
  - Repos ranked by risk score
- [ ] Backend endpoint:
  ```python
  @router.get("/api/v1/analytics")
  async def get_analytics(user_id: int, days: int = 30):
      # Return aggregated metrics for charts
      return {
          "vuln_trend": [{"date": "2024-01-15", "found": 3, "fixed": 2}, ...],
          "top_vulns": [{"type": "SQL Injection", "count": 12}, ...],
          "mttr_hours": 4.2,
          "fix_rate": 0.89,
          ...
      }
  ```
- [ ] Use Recharts or similar for interactive charts

**Verification:**
- Analytics page loads with real data
- Charts update as new scans complete
- MTTR is accurately calculated from scan timestamps

---

## Task 7.7: Repository Security Scorecard

**Files:** NEW `components/SecurityScorecard.tsx`, `app/repos/[id]/page.tsx`

**Steps:**
- [ ] Generate a letter grade (A-F) for each repo based on:
  - Vulnerability rate (vulns per scan)
  - Fix rate (% fixed)
  - MTTR (time to fix)
  - Open vulnerability count
  - Dependency health
- [ ] Display scorecard on repo detail page
- [ ] Add GitHub badge generation:
  ```
  ![Aegis Score](https://your-aegis.com/badge/repo-name)
  ```

**Verification:**
- Repos with no vulns → A grade
- Repos with open CRITICALs → D/F grade
- Badge renders correctly in README

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 7.1 | PR-targeted scanning | 🔴 Critical | Pipeline, `main.py` |
| 7.2 | Dependency scanning | 🟠 High | NEW `scanner/dependency_scanner.py` |
| 7.3 | Slack/Discord notifications | 🟡 Medium | NEW `notifications/` |
| 7.4 | Regression detection | 🟡 Medium | Pipeline, DB |
| 7.5 | Multi-language support | 🟡 Medium | Config, scanner, agents |
| 7.6 | Analytics dashboard | 🟡 Medium | Frontend, backend |
| 7.7 | Repository scorecard | 🟢 Nice-to-have | Frontend, backend |

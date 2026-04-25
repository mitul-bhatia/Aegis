# Phase 1 — Security & Reliability Fixes

> **Priority:** 🔴 CRITICAL — Complete before any other phase
>
> **Estimated effort:** 2-3 days
>
> **Goal:** Eliminate every known security vulnerability and reliability bug in the current codebase.

---

## Task 1.1: Remove Docker Subprocess Fallback

**Files:** `sandbox/docker_runner.py`

**Current problem:** When Docker daemon is unavailable, exploit scripts run as raw `subprocess.run()` on the host machine — no isolation, no memory limits, full network access. This is the most dangerous bug in the codebase.

**Steps:**
- [ ] Remove the entire `if not docker_client:` fallback block in `run_exploit_in_sandbox()` (lines 39-101)
- [ ] Remove the `if not docker_client:` fallback block in `run_tests_in_sandbox()` (lines 198-235)
- [ ] Replace both with a hard failure:
  ```python
  if not docker_client:
      logger.error("Docker daemon unavailable — refusing to execute untrusted code")
      return {
          "exit_code": -1,
          "stdout": "",
          "stderr": "SANDBOX_UNAVAILABLE: Docker daemon is not running. Cannot execute exploit safely.",
          "exploit_succeeded": False,
          "vulnerability_confirmed": False,
          "output_summary": "Sandbox unavailable — scan aborted for security"
      }
  ```
- [ ] Update orchestrator to recognize `SANDBOX_UNAVAILABLE` and set scan status to `failed` with a clear message
- [ ] Keep the DEMO_MODE bypass since it's a separate, intentional override

**Verification:**
- Stop Docker, trigger a scan — should fail cleanly, NOT run subprocess
- Start Docker, trigger a scan — should work normally

---

## Task 1.2: Encrypt GitHub Tokens at Rest

**Files:** `database/models.py`, `routes/auth.py`, `routes/repos.py`, `orchestrator.py`, `config.py`, `.env`

**Current problem:** `User.github_token` stored as plaintext `String` column. DB leak = every user's GitHub access compromised.

**Steps:**
- [ ] Add `cryptography` to `requirements.txt`
- [ ] Add `FERNET_KEY` to `.env` and `.env.example` — generate with:
  ```python
  from cryptography.fernet import Fernet
  print(Fernet.generate_key().decode())
  ```
- [ ] Add `FERNET_KEY` to `config.py`
- [ ] Create `utils/crypto.py`:
  ```python
  from cryptography.fernet import Fernet
  import config
  
  _fernet = Fernet(config.FERNET_KEY.encode()) if config.FERNET_KEY else None
  
  def encrypt_token(token: str) -> str:
      if not _fernet:
          return token  # Fallback for dev without key
      return _fernet.encrypt(token.encode()).decode()
  
  def decrypt_token(encrypted: str) -> str:
      if not _fernet:
          return encrypted
      try:
          return _fernet.decrypt(encrypted.encode()).decode()
      except Exception:
          return encrypted  # Probably unencrypted legacy token
  ```
- [ ] Update `routes/auth.py`: encrypt before storing: `user.github_token = encrypt_token(access_token)`
- [ ] Update ALL places that READ `github_token` to decrypt first:
  - `orchestrator.py` line 187: `user_token = decrypt_token(repo_obj.user.github_token)`
  - `routes/repos.py` line 236: `webhook_token = decrypt_token(user.github_token)`
  - `routes/repos.py` line 252: `decrypt_token(user.github_token)`
  - `routes/repos.py` line 311: `decrypt_token(user.github_token)`
  - `scheduler.py` line 92: add token decryption

**Verification:**
- Check DB after login — `github_token` should be encrypted (starts with `gAAAAA...`)
- All features (webhook install, clone, PR creation) still work with decrypted tokens
- Old unencrypted tokens should still work (graceful fallback in `decrypt_token`)

---

## Task 1.3: Move Auth from localStorage to httpOnly Cookies

**Files:** `routes/auth.py`, `aegis-frontend/lib/api.ts`, `aegis-frontend/app/auth/callback/page.tsx`, `aegis-frontend/app/dashboard/page.tsx`

**Current problem:** `localStorage.setItem('github_token', ...)` — any XSS can steal the token.

**Steps:**
- [ ] Backend: After OAuth callback, set an httpOnly cookie with user_id:
  ```python
  from fastapi.responses import JSONResponse
  
  response = JSONResponse(content={"id": user.id, "github_username": user.github_username, ...})
  response.set_cookie(
      key="aegis_session",
      value=str(user.id),  # or a signed JWT
      httponly=True,
      secure=False,  # True in production with HTTPS
      samesite="lax",
      max_age=86400 * 7,  # 7 days
      path="/"
  )
  return response
  ```
- [ ] Add a `/api/auth/me` endpoint that reads the cookie and returns user info
- [ ] Frontend: Remove `localStorage.setItem('user_id', ...)` and `localStorage.setItem('github_token', ...)`
- [ ] Frontend: Use `credentials: 'include'` in all fetch calls
- [ ] Frontend: Replace `localStorage.getItem('user_id')` checks with a call to `/api/auth/me`
- [ ] Add CORS `allow_credentials=True` (already set in `main.py`)
- [ ] Add a logout endpoint that clears the cookie

**Verification:**
- Login flow works and no token appears in localStorage
- Refreshing the page keeps the session
- Logout clears the session
- Opening DevTools → Application → Local Storage shows no sensitive data

---

## Task 1.4: Enforce Structured JSON Output from LLMs

**Files:** `agents/finder.py`, `agents/exploiter.py`, `agents/engineer.py`

**Current problem:** JSON parsing uses regex fallback (`re.findall(r'\{[^{}]+\}', ...)`) which silently extracts partial/corrupted JSON.

**Steps:**
- [ ] **finder.py**: Add `response_format={"type": "json_object"}` to Groq API call
  ```python
  response = client.chat.completions.create(
      model=config.HACKER_MODEL,
      max_tokens=config.HACKER_MAX_TOKENS,
      response_format={"type": "json_object"},  # ← ADD THIS
      messages=[...]
  )
  ```
  - Update system prompt to mention "Output ONLY a JSON object with a 'findings' key containing an array"
  - Remove the regex fallback entirely — if JSON is invalid, retry once, then return empty list
  - Validate each finding with Pydantic `VulnerabilityFinding(**item)` and skip invalid ones

- [ ] **exploiter.py**: No JSON output needed (produces Python code), but clean up the markdown fence stripping to be more robust
  ```python
  import re
  exploit_script = re.sub(r'^```\w*\n?', '', exploit_script)
  exploit_script = re.sub(r'\n?```$', '', exploit_script)
  exploit_script = exploit_script.strip()
  ```

- [ ] **engineer.py**: Add `response_format={"type": "json_object"}` to Mistral API call
  - Update system prompt: "Output a JSON object with keys: patched_code, test_code"
  - Add Pydantic validation for Engineer output:
    ```python
    class EngineerOutput(BaseModel):
        patched_code: str
        test_code: str = ""
    ```
  - Remove regex fallback, add retry on parse failure

**Verification:**
- Trigger a scan and check logs — no "regex extraction" or "fallback" warnings
- All three agents produce clean, validated output
- Deliberately test with a model that produces markdown fences — should be handled cleanly

---

## Task 1.5: Add Duplicate Webhook/Scan Prevention

**Files:** `main.py`, `orchestrator.py`

**Current problem:** GitHub sends duplicate webhooks (retries). Two identical scans can start simultaneously.

**Steps:**
- [ ] In `orchestrator.py` `_create_scan()`, check for existing scan with same `commit_sha` + `repo_id`:
  ```python
  def _create_scan(db, repo_id, commit_sha: str, branch: str) -> Scan:
      # Check for duplicate
      existing = db.query(Scan).filter_by(
          repo_id=repo_id,
          commit_sha=commit_sha
      ).first()
      if existing:
          logger.info(f"Duplicate scan for {commit_sha[:8]} — returning existing scan {existing.id}")
          return existing  # Return existing instead of creating new
      
      scan = Scan(repo_id=repo_id, commit_sha=commit_sha, branch=branch, ...)
      ...
  ```
- [ ] In `run_aegis_pipeline()`, check if the returned scan is already in a terminal state:
  ```python
  if scan.status in [ScanStatus.FIXED.value, ScanStatus.CLEAN.value, ScanStatus.FAILED.value, ...]:
      logger.info(f"Scan {scan.id} already completed — skipping duplicate run")
      return
  ```

**Verification:**
- Send the same webhook payload twice — only one scan should be created
- The second webhook should return quickly without starting a new pipeline

---

## Task 1.6: Add Fork PR Rejection

**Files:** `main.py`

**Current problem:** PRs from forks run the pipeline on potentially malicious code. A fork PR could contain exploit code targeting Aegis itself.

**Steps:**
- [ ] In the `pull_request` handler in `main.py`, add fork check:
  ```python
  if action in ("opened", "synchronize"):
      pr = payload["pull_request"]
      
      # Security: never process PRs from forks
      if pr["head"]["repo"]["fork"]:
          logger.warning(f"Ignoring fork PR #{pr['number']} from {pr['head']['repo']['full_name']} — security policy")
          return {"message": "Fork PRs are not scanned for security reasons"}
      
      push_info = { ... }
  ```

**Verification:**
- Fork PRs should be rejected with a clear message in logs
- Same-repo PRs should work normally

---

## Task 1.7: Delete the `aegis.db` and Regenerate

**Context:** After encrypting tokens (Task 1.2), existing plaintext tokens are a liability.

**Steps:**
- [ ] Back up `aegis.db` (in case you need old scan data for reference)
- [ ] Delete `aegis.db` — the `init_db()` call on next startup will recreate it
- [ ] Re-login to Aegis — new token will be encrypted
- [ ] Re-add repositories

> **Note:** This will be the LAST time we delete the DB. Phase 4 adds Alembic migrations.

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 1.1 | Remove subprocess fallback | 🔴 Critical | `sandbox/docker_runner.py` |
| 1.2 | Encrypt GitHub tokens | 🔴 Critical | `models.py`, `auth.py`, `repos.py`, `orchestrator.py` |
| 1.3 | httpOnly cookie auth | 🟠 High | `auth.py`, `api.ts`, callback/page, dashboard |
| 1.4 | Structured JSON output | 🔴 Critical | `finder.py`, `exploiter.py`, `engineer.py` |
| 1.5 | Duplicate scan prevention | 🟠 High | `main.py`, `orchestrator.py` |
| 1.6 | Fork PR rejection | 🟡 Medium | `main.py` |
| 1.7 | DB reset (post-encryption) | 🟡 Medium | — |

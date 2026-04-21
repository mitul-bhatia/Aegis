# 🛡️ Aegis — Beginner-Friendly Development Guide
## Build It Step by Step — No Experience Assumed

> **What is Aegis?**
> Aegis is a system that automatically finds security holes in code, proves they're real, fixes them, and opens a Pull Request — all without a human doing anything.
>
> **Who this guide is for:** Someone who knows basic Python but has never built something like this before. Every decision is explained. Every code block is commented. Nothing is assumed.

---

## 🧭 How to Use This Guide

Read top to bottom. Don't skip phases. Each phase ends with a test you run in your terminal — **only move to the next phase when that test passes.**

```
Phase 0 → Set up your computer (30 min)
Phase 1 → Receive GitHub notifications when someone pushes code (1 hour)
Phase 2 → Read what changed + scan for problems (1 hour)
Phase 3 → Give the AI memory of the entire codebase (2 hours)
Phase 4 → AI writes an attack script to prove the bug is real (2 hours)
Phase 5 → Run the attack safely inside a locked container (1.5 hours)
Phase 6 → AI writes a fix (1.5 hours)
Phase 7 → Check if the fix actually works (1 hour)
Phase 8 → Open a Pull Request with all the evidence (45 min)
Phase 9 → Connect everything and do a full test (1 hour)
```

---

## 📚 Concepts You Need to Understand First

Before writing any code, read this section. It will save you hours of confusion.

### What is a Webhook?

Normally, your code sits and waits. A webhook flips this around — **GitHub calls YOUR server** the moment something happens (like someone pushing a commit). Think of it like signing up for text alerts from your bank. You don't check your balance every minute — the bank texts you when something happens.

```
Normal polling (BAD):          Webhook (GOOD):
Your server → GitHub           GitHub → Your server
"Anything new?"                "Hey, someone just pushed!"
"Nope"
"Anything new?"
"Nope"
(every 30 seconds, forever)
```

### What is RAG?

RAG stands for **Retrieval-Augmented Generation**. In plain English: instead of feeding the AI your entire codebase (which is slow, expensive, and confusing), you:
1. Index everything once (like building a book's index)
2. On each commit, look up only the relevant pages

```
Without RAG:                   With RAG:
"Here are all 10,000 files,   "Here are the 5 files most
 please find the bug"          likely related to this change"
→ Slow, expensive, confused   → Fast, cheap, focused
```

### What is Docker and Why Do We Need It?

The AI writes real attack scripts. If you run those on your own computer without protection:
- The script could read your passwords
- Could delete your files
- Could make network requests

Docker is like a **disposable cardboard box** — the script runs inside it, can't see outside, and when it's done you throw the box away. Even if the script does something destructive, it only destroys the box.

### What is MCP?

MCP (Model Context Protocol) is a standard way to give AI agents access to tools. Instead of writing custom code to connect the AI to Semgrep, GitHub, Docker, etc., you just "plug in" an MCP server — like USB devices. The AI automatically discovers what tools are available and uses them.

### What is Semgrep?

Semgrep is a free tool that scans code for known dangerous patterns (like SQL injection, insecure passwords, etc.). It's our **cheap first filter** — we run Semgrep first because it's fast and free. Only if Semgrep finds something suspicious do we bring in the expensive AI.

---

## Phase 0 — Setting Up Your Computer

**What we're doing:** Installing all the software Aegis needs to run.

### Step 0.1 — Create the project folder structure

Open your terminal and run these commands one by one:

```bash
# Create the main project folder and enter it
mkdir aegis && cd aegis

# Create subfolders — each one holds code for a specific part of Aegis
mkdir -p agents rag sandbox github scanner

# Create all the Python files we'll fill in later
# (These start empty — we add code in each phase)
touch main.py orchestrator.py

# Agent files — each "agent" is an AI with a specific job
touch agents/__init__.py agents/hacker.py agents/engineer.py agents/reviewer.py

# RAG files — for giving the AI memory of the codebase
touch rag/__init__.py rag/indexer.py rag/retriever.py

# Sandbox files — for running code safely in Docker
touch sandbox/__init__.py sandbox/docker_runner.py

# GitHub files — for talking to GitHub's API
touch github/__init__.py github/webhook.py github/pr_creator.py github/diff_fetcher.py

# Scanner file — for running Semgrep
touch scanner/__init__.py scanner/semgrep_runner.py
```

### Step 0.2 — Install Python libraries

```bash
# Create a virtual environment
# This keeps Aegis's libraries separate from other Python projects on your computer
python -m venv venv

# Activate it (you must do this every time you open a new terminal)
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows — use this line instead

# Now install everything Aegis needs:
pip install fastapi              # Web server (receives GitHub webhooks)
pip install uvicorn              # Runs the FastAPI server
pip install python-dotenv        # Loads secrets from a .env file
pip install anthropic            # Talks to Claude AI
pip install chromadb             # Local database for storing code embeddings
pip install PyGithub             # Talks to GitHub's API
pip install gitpython            # Runs git commands from Python
pip install docker               # Controls Docker containers from Python
pip install requests             # Makes HTTP requests
pip install semgrep              # The Semgrep security scanner

# Verify semgrep installed correctly
semgrep --version
# You should see something like: semgrep 1.x.x
```

### Step 0.3 — Create your secrets file

Create a file called `.env` in the `aegis/` folder. This holds your private keys — **never commit this file to git.**

```bash
# .env
# Replace the placeholder values with your actual keys

# Get this from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Get this from: https://github.com/settings/tokens
# Needs permissions: repo, pull_requests, webhooks
GITHUB_TOKEN=ghp_your-token-here

# You make this up — any random string (e.g. "my-secret-abc123")
# You'll paste this into GitHub's webhook settings later
GITHUB_WEBHOOK_SECRET=your-random-secret-string

# The Claude model to use
CLAUDE_MODEL=claude-sonnet-4-6

# Port for the web server
PORT=8000
```

### Step 0.4 — Create a fake "vulnerable" repo to test with

We need a test repo with intentionally broken code so we can see Aegis work end-to-end.

```bash
# Create a new folder for our test repo
mkdir test_repo && cd test_repo

# Initialize it as a git repository
git init

# Create a Python file with two intentional SQL injection vulnerabilities
# SQL injection = a hacker can type special characters to steal all data
cat > app.py << 'EOF'
import sqlite3

# ⚠️  VULNERABILITY 1: SQL Injection in get_user()
# The problem: we're directly inserting the username into the SQL string.
# A hacker can pass: username = "' OR '1'='1"
# And the query becomes: SELECT * FROM users WHERE username = '' OR '1'='1'
# That '1'='1' is always true, so it returns EVERY user in the database!
def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# ⚠️  VULNERABILITY 2: SQL Injection in get_product()
def get_product(product_id):
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE id = {product_id}")
    return cursor.fetchone()
EOF

# Create a basic test file
cat > test_app.py << 'EOF'
# These are placeholder tests.
# In a real project, these would test actual database logic.
def test_get_user_normal():
    assert True  # Placeholder

def test_get_product_normal():
    assert True  # Placeholder
EOF

# Commit the files to git
git add .
git commit -m "Initial commit with vulnerable code"

# Go back to the main aegis folder
cd ..
```

### ✅ Phase 0 Test — Does everything import?

```bash
# Run this in your terminal (inside the aegis folder, with venv activated)
python -c "import anthropic, chromadb, fastapi, docker; print('✅ All imports OK')"

# You should see: ✅ All imports OK
# If you see an error, re-run the pip install command for that library
```

---

## Phase 1 — Receiving GitHub Push Notifications

**What we're building:** A web server that GitHub can call whenever someone pushes code. Like setting up a doorbell — when someone pushes, GitHub rings our bell.

**Why FastAPI?** FastAPI is a modern Python web framework. It's fast, simple, and automatically generates documentation. We use it to create the URL that GitHub will call.

### Step 1.1 — Verify that the message is really from GitHub

When GitHub calls our server, it signs the message so we can verify it's legitimate (not someone else pretending to be GitHub).

```python
# github/webhook.py

import hashlib  # For creating hash signatures
import hmac     # For comparing signatures securely
import os       # For reading environment variables

# Load our webhook secret from the .env file
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    GitHub signs every webhook message it sends us.
    This function checks: "Did this message really come from GitHub?"
    
    How it works:
    - GitHub takes the message body + our secret and creates a hash
    - We do the same math on our end
    - If the hashes match, the message is authentic
    
    payload_body: The raw bytes of the incoming request
    signature_header: The hash GitHub sent in the request headers
    Returns: True if message is from GitHub, False if it's fake
    """
    if not signature_header:
        return False  # No signature at all = definitely not from GitHub
    
    # Create the expected hash using our secret
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),   # Our secret key
        msg=payload_body,                  # The message to hash
        digestmod=hashlib.sha256           # SHA-256 algorithm
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    # Compare in a way that's safe against timing attacks
    # (Don't use == here — it can leak information about the secret)
    return hmac.compare_digest(expected_signature, signature_header)


def extract_push_info(payload: dict) -> dict:
    """
    GitHub sends us a big JSON object with lots of info about the push.
    This function pulls out only the parts we actually need.
    
    payload: The full JSON from GitHub
    Returns: A smaller dict with just what Aegis needs
    """
    return {
        # Who owns the repo and what it's called (e.g., "alice/my-app")
        "repo_name": payload["repository"]["full_name"],
        
        # The URL we can use to clone the repo
        "repo_url": payload["repository"]["clone_url"],
        
        # Which branch was pushed to (e.g., "main" or "feature/login")
        "branch": payload["ref"].replace("refs/heads/", ""),
        
        # The unique ID of the latest commit (a long hex string like "a3f8d2...")
        "commit_sha": payload["after"],
        
        # What the developer wrote as their commit message
        "commit_message": payload["head_commit"]["message"],
        
        # The GitHub username of who pushed the code
        "pusher": payload["pusher"]["name"],
        
        # List of files that were added or changed in this push
        "files_changed": [
            f
            for commit in payload.get("commits", [])
            for f in commit.get("added", []) + commit.get("modified", [])
        ]
    }
```

### Step 1.2 — The main web server

```python
# main.py

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv  # Loads variables from .env file
import json

# Load our .env file so os.getenv() works
load_dotenv()

from github.webhook import verify_signature, extract_push_info

# Create the FastAPI app — this is our web server
app = FastAPI(title="Aegis Security System")


@app.get("/health")
async def health():
    """
    A simple endpoint to check if Aegis is running.
    Visit http://localhost:8000/health in your browser to verify.
    """
    return {"status": "Aegis is running", "version": "0.1.0"}


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    This is the URL you paste into GitHub's webhook settings.
    GitHub calls this every time someone pushes code.
    
    The function:
    1. Reads the incoming request
    2. Verifies it's really from GitHub
    3. Extracts the useful info
    4. Triggers our analysis pipeline in the background
    """
    
    # Read the raw bytes of the request body
    # We need the raw bytes (not parsed JSON) for signature verification
    body = await request.body()
    
    # Check that this request actually came from GitHub
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        # Someone sent us a fake webhook — reject it
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # GitHub sends different event types (push, pull_request, issues, etc.)
    # We only care about push events
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "push":
        return {"message": f"Ignoring event type: {event_type}"}
    
    # Parse the JSON body now that we know it's authentic
    payload = json.loads(body)
    push_info = extract_push_info(payload)
    
    # Log that we received something (helpful for debugging)
    print(f"[AEGIS] Push received: {push_info['commit_sha'][:8]} on {push_info['repo_name']}")
    print(f"[AEGIS] Files changed: {push_info['files_changed']}")
    
    # Run our analysis in the background
    # This is important! GitHub expects a fast response (within a few seconds)
    # If we do all the AI analysis before responding, GitHub will time out
    # background_tasks.add_task(run_aegis_pipeline, push_info)
    # ↑ We'll uncomment this in Phase 9 once we've built everything
    
    # Immediately respond to GitHub so it knows we got the message
    return {"message": "Webhook received", "commit": push_info["commit_sha"][:8]}


# This block runs the server when you execute: python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    # reload=True means the server restarts automatically when you save changes
```

### Step 1.3 — Start the server and expose it to the internet

GitHub needs to reach your server. If you're developing locally, your laptop isn't publicly accessible. We use **ngrok** to create a temporary public tunnel.

```bash
# Terminal 1: Start Aegis
python main.py
# You should see: Uvicorn running on http://0.0.0.0:8000

# Terminal 2: Install ngrok from https://ngrok.com/download, then run:
ngrok http 8000
# You'll see a line like: Forwarding https://abc123.ngrok.io -> localhost:8000
# Copy that https://abc123.ngrok.io URL — you'll need it for GitHub
```

**Setting up the GitHub webhook:**
1. Go to your test repo on GitHub
2. Click **Settings** → **Webhooks** → **Add webhook**
3. **Payload URL:** `https://abc123.ngrok.io/webhook/github`
4. **Content type:** `application/json`
5. **Secret:** The value you put in `.env` for `GITHUB_WEBHOOK_SECRET`
6. **Which events:** Select "Just the push event"
7. Click **Add webhook**

### ✅ Phase 1 Test

```bash
# Test 1: Is the server running?
curl http://localhost:8000/health
# Expected: {"status":"Aegis is running","version":"0.1.0"}

# Test 2: Does signature checking work?
# (This should fail because we're sending a fake signature)
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=fakesignature" \
  -d '{"test": true}'
# Expected: {"detail":"Invalid signature"}
# ← Good! This means our security check is working.

# Test 3: Make a real push
cd test_repo
echo "# test change" >> app.py
git add . && git commit -m "Test push for Aegis"
git push

# Watch Terminal 1 — you should see:
# [AEGIS] Push received: abc12345 on yourname/test-repo
# [AEGIS] Files changed: ['app.py']
```

**Common mistakes:**
- `Invalid signature` when testing with real GitHub → Double-check that the secret in `.env` exactly matches what you typed into GitHub's webhook settings
- Server not receiving anything → Make sure ngrok is running and the URL in GitHub matches

---

## Phase 2 — Reading What Changed + First Security Scan

**What we're building:** Two things:
1. A function to fetch the actual code diff from GitHub (what lines changed?)
2. A Semgrep scan on only the changed files (are there any suspicious patterns?)

**Why scan first with Semgrep before using the AI?** Semgrep is free and instant. Claude costs money per call. If Semgrep finds nothing suspicious, we can skip the expensive AI entirely. This is called a "cheap filter before the expensive step."

### Step 2.1 — Fetch the diff from GitHub

```python
# github/diff_fetcher.py

import subprocess  # For running shell commands (git clone, git pull)
import os
from github import Github  # The PyGithub library for GitHub's API

# Load the GitHub token from .env
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def clone_or_pull_repo(repo_url: str, local_path: str) -> str:
    """
    Download the repository to our server so we can scan it.
    
    - If we've never seen this repo: clone it (full download)
    - If we already have it: pull the latest changes (faster)
    
    repo_url: The GitHub URL to clone (e.g., https://github.com/alice/app.git)
    local_path: Where to save it on our server (e.g., ./repos/alice_app)
    Returns: The local_path so callers can use it
    """
    if os.path.exists(local_path):
        # We already have the repo — just get the latest commits
        print(f"[GIT] Pulling latest changes into {local_path}")
        subprocess.run(["git", "-C", local_path, "pull"], capture_output=True)
    else:
        # First time seeing this repo — download everything
        print(f"[GIT] Cloning {repo_url} into {local_path}")
        subprocess.run(["git", "clone", repo_url, local_path], capture_output=True)
    
    return local_path


def get_diff(repo_full_name: str, commit_sha: str) -> dict:
    """
    Get the list of files changed in a specific commit, with the actual diffs.
    
    repo_full_name: e.g., "alice/my-app"
    commit_sha: The commit ID (e.g., "a3f8d2e1b9...")
    Returns: A dict with all changed files and their diffs
    """
    # Connect to GitHub using our token
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    
    # Fetch info about this specific commit
    commit = repo.get_commit(commit_sha)
    
    # We only care about code files, not config/docs/images
    CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}
    
    changed_files = []
    for file in commit.files:
        # Get the file extension (e.g., ".py" from "app.py")
        _, ext = os.path.splitext(file.filename)
        
        if ext not in CODE_EXTENSIONS:
            continue  # Skip non-code files
        
        changed_files.append({
            "filename": file.filename,         # e.g., "src/auth/login.py"
            "status": file.status,             # "added", "modified", or "removed"
            "additions": file.additions,       # Number of lines added
            "deletions": file.deletions,       # Number of lines removed
            "patch": file.patch or "",         # The actual diff (+ and - lines)
        })
    
    return {
        "commit_sha": commit_sha,
        "commit_message": commit.commit.message,
        "changed_files": changed_files,
        # Total lines touched — useful for deciding if this is a big or small change
        "total_changes": sum(f["additions"] + f["deletions"] for f in changed_files)
    }
```

### Step 2.2 — Run Semgrep on the changed files

```python
# scanner/semgrep_runner.py

import subprocess  # For running the semgrep command
import json        # For parsing semgrep's JSON output
import os


def run_semgrep_on_files(file_paths: list, repo_path: str) -> list:
    """
    Run Semgrep on a list of files and return any security findings.
    
    Semgrep checks for common vulnerability patterns like:
    - SQL injection (inserting user input directly into SQL queries)
    - XSS (inserting user input directly into HTML)
    - Hardcoded passwords
    - Insecure use of cryptography
    - And thousands more...
    
    file_paths: List of relative file paths (e.g., ["src/auth.py", "app.py"])
    repo_path: The local folder where the repo lives
    Returns: List of findings, each describing one potential vulnerability
    """
    if not file_paths:
        return []  # Nothing to scan
    
    # Build the full paths to each file
    full_paths = [
        os.path.join(repo_path, f)
        for f in file_paths
        if os.path.exists(os.path.join(repo_path, f))  # Only scan files that exist
    ]
    
    if not full_paths:
        return []
    
    # Build the semgrep command
    # --config auto  → Automatically pick the best rules for each language
    # --json         → Output results as JSON (easier to parse than plain text)
    # --quiet        → Don't show progress bars (cleaner output)
    cmd = [
        "semgrep",
        "--config", "auto",
        "--json",
        "--quiet",
        "--no-git-ignore",
        *full_paths  # Add all file paths at the end
    ]
    
    # Run semgrep and capture output
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    # Semgrep exit codes: 0 = no findings, 1 = findings found, other = error
    if result.returncode not in [0, 1]:
        print(f"[SEMGREP] Error running scan: {result.stderr}")
        return []
    
    try:
        # Parse the JSON output
        output = json.loads(result.stdout)
        
        findings = []
        for finding in output.get("results", []):
            findings.append({
                # The rule ID tells us what kind of vulnerability was found
                # e.g., "python.lang.security.audit.formatted-sql-query"
                "rule_id": finding["check_id"],
                
                # How serious is this? "ERROR", "WARNING", or "INFO"
                "severity": finding["extra"]["severity"],
                
                # A human-readable description of the problem
                "message": finding["extra"]["message"],
                
                # Which file has the problem
                "file": finding["path"],
                
                # Which lines to look at
                "line_start": finding["start"]["line"],
                "line_end": finding["end"]["line"],
                
                # The actual code that triggered the rule
                "code_snippet": finding["extra"]["lines"],
                
                # Category like "security", "correctness", "performance"
                "category": finding["extra"].get("metadata", {}).get("category", "unknown")
            })
        
        return findings
    
    except json.JSONDecodeError:
        # Semgrep output wasn't valid JSON — happens sometimes with unusual code
        print("[SEMGREP] Could not parse output as JSON")
        return []


def format_findings_for_llm(findings: list) -> str:
    """
    Convert Semgrep's raw output into a readable summary for Claude.
    The AI understands natural language better than raw JSON.
    
    findings: The list returned by run_semgrep_on_files()
    Returns: A nicely formatted string Claude can understand
    """
    if not findings:
        return "Semgrep found no issues."
    
    formatted = f"Semgrep found {len(findings)} potential issue(s):\n\n"
    
    for i, f in enumerate(findings, 1):
        formatted += f"""Issue {i}:
  Type of problem: {f['rule_id']}
  Severity: {f['severity']}
  File: {f['file']} (line {f['line_start']})
  What's wrong: {f['message']}
  The problematic code: {f['code_snippet']}

"""
    return formatted
```

### ✅ Phase 2 Test

Create a file called `test_phase2.py` and run it:

```python
# test_phase2.py
import os, sys
sys.path.insert(0, ".")

from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm
import tempfile

print("Testing Semgrep scanner...")

# Create a temporary folder with a vulnerable Python file
with tempfile.TemporaryDirectory() as tmpdir:
    
    # Write a file with a known SQL injection vulnerability
    vuln_file = os.path.join(tmpdir, "test.py")
    with open(vuln_file, "w") as f:
        f.write("""
import sqlite3
def get_user(name):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    # This is vulnerable — name is inserted directly into the SQL string
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchone()
""")
    
    # Run Semgrep on our vulnerable file
    findings = run_semgrep_on_files(["test.py"], tmpdir)
    
    print(f"✅ Semgrep found {len(findings)} finding(s)")
    
    if findings:
        print(f"   Rule triggered: {findings[0]['rule_id']}")
        print(f"   Severity: {findings[0]['severity']}")
        print(f"\nFormatted output for AI:\n")
        print(format_findings_for_llm(findings))
    else:
        print("   ⚠️  Expected to find SQL injection but didn't — check semgrep rules")
```

```bash
python test_phase2.py
# Expected output:
# ✅ Semgrep found 1 finding(s)
#    Rule triggered: python.lang.security.audit.formatted-sql-query...
#    Severity: WARNING
```

---

## Phase 3 — Giving the AI Memory of the Codebase (RAG)

**What we're building:** A searchable index of the entire codebase. Built once when a repo is first connected, then searched on every commit to give the AI relevant context.

**Think of it like a librarian:** When a commit comes in changing the `login()` function, the librarian quickly finds: "Here are all the files that use `login()`, here are the routes that call it, here are the tests for it." The AI gets a focused picture instead of the entire library.

### Step 3.1 — The Indexer (runs once per repo)

```python
# rag/indexer.py

import os
import ast       # Python's built-in parser — reads Python code structure
import chromadb  # Our local vector database

# Connect to ChromaDB — this stores data in a folder called aegis_vector_db
# PersistentClient means data survives between runs (unlike in-memory)
chroma_client = chromadb.PersistentClient(path="./aegis_vector_db")


def get_or_create_collection(repo_name: str):
    """
    Each repo gets its own "collection" in ChromaDB.
    Think of a collection like a table in a regular database.
    
    repo_name: e.g., "alice/my-app"
    Returns: The ChromaDB collection object for this repo
    """
    # Collection names can't have slashes or hyphens, so we replace them
    safe_name = repo_name.replace("/", "_").replace("-", "_")
    
    return chroma_client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"}  # cosine = compare by meaning, not exact text
    )


def extract_file_metadata(file_path: str, content: str) -> dict:
    """
    Extract useful facts about a code file.
    
    Instead of storing raw code (which would be huge), we store a summary:
    - What functions does this file define?
    - What does it import?
    - Does it touch databases, authentication, or HTTP?
    
    file_path: Relative path like "src/auth/login.py"
    content: The full text of the file
    Returns: A dict of facts about this file
    """
    metadata = {
        "file": file_path,
        "functions": [],   # Function names defined in this file
        "imports": [],     # Libraries/modules this file imports
        "classes": [],     # Class names defined in this file
        
        # These flags help us quickly find security-relevant files
        "has_sql": "sql" in content.lower() or "SELECT" in content or "INSERT" in content,
        "has_auth": any(w in content.lower() for w in ["password", "token", "auth", "login", "jwt"]),
        "has_http": any(w in content.lower() for w in ["request", "response", "route", "endpoint"]),
    }
    
    # For Python files, use the AST parser to get exact function/class names
    if file_path.endswith(".py"):
        try:
            # Parse the Python code into a tree structure
            tree = ast.parse(content)
            
            # Walk through every node in the tree
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Found a function definition — add its name
                    metadata["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    # Found an import statement — add the module name
                    for alias in node.names:
                        metadata["imports"].append(alias.name)
                elif isinstance(node, ast.ClassDef):
                    # Found a class definition — add its name
                    metadata["classes"].append(node.name)
        except SyntaxError:
            # File has syntax errors — skip the AST parsing but still index it
            pass
    
    return metadata


def index_repository(repo_path: str, repo_name: str) -> int:
    """
    Walk through the entire repo and index every code file.
    
    This runs ONCE when a repo is first connected to Aegis.
    After this, we only need to do small lookups on each commit.
    
    repo_path: Local path to the cloned repo (e.g., "./repos/alice_my-app")
    repo_name: Full repo name (e.g., "alice/my-app")
    Returns: Number of files indexed
    """
    collection = get_or_create_collection(repo_name)
    
    # File types we understand and should index
    SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}
    
    # Folders we should skip (not real code)
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    
    indexed = 0
    
    # os.walk() gives us every folder and file in the repo
    for root, dirs, files in os.walk(repo_path):
        
        # Remove skip directories from the list so os.walk doesn't enter them
        # We modify dirs in-place — this is how os.walk skipping works
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for filename in files:
            # Only process code files
            _, ext = os.path.splitext(filename)
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            
            file_path = os.path.join(root, filename)
            # Store relative path (e.g., "src/auth.py" not "/full/path/src/auth.py")
            relative_path = os.path.relpath(file_path, repo_path)
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                if len(content) < 10:
                    continue  # Skip basically empty files
                
                metadata = extract_file_metadata(relative_path, content)
                
                # Build a rich text description of this file for embedding
                # This is what ChromaDB will use for semantic search
                text_to_embed = f"""
File: {relative_path}
Functions defined here: {', '.join(metadata['functions'][:10])}
Classes defined here: {', '.join(metadata['classes'][:5])}
Imports used: {', '.join(metadata['imports'][:10])}
Touches database (SQL): {metadata['has_sql']}
Handles authentication: {metadata['has_auth']}
Handles HTTP requests: {metadata['has_http']}

First 1000 chars of code:
{content[:1000]}
"""
                
                # Store in ChromaDB
                # upsert = insert if new, update if already exists
                collection.upsert(
                    ids=[relative_path],       # Unique ID for this file
                    documents=[text_to_embed], # What to search against
                    metadatas=[{
                        "file_path": relative_path,
                        "functions": str(metadata["functions"]),
                        "has_sql": metadata["has_sql"],
                        "has_auth": metadata["has_auth"],
                        "has_http": metadata["has_http"],
                        # Store the first 500 chars to show as context later
                        "content_preview": content[:500]
                    }]
                )
                
                indexed += 1
                print(f"  [RAG] Indexed: {relative_path}")
                
            except Exception as e:
                # Don't crash if one file fails — just skip it
                print(f"  [RAG] Skipped {relative_path}: {e}")
    
    print(f"[RAG] Done! Indexed {indexed} files for {repo_name}")
    return indexed
```

### Step 3.2 — The Retriever (runs on every commit)

```python
# rag/retriever.py

from rag.indexer import get_or_create_collection


def retrieve_relevant_context(
    repo_name: str,
    diff: dict,
    semgrep_findings: list,
    top_k: int = 5
) -> str:
    """
    Given a commit diff, find the most relevant files from our index.
    
    Example: If a commit changes `authenticate_user()`, this function finds:
    - All files that import `authenticate_user`
    - The test file for authentication
    - Middleware that wraps auth
    
    repo_name: e.g., "alice/my-app"
    diff: The result from get_diff() — what changed in this commit
    semgrep_findings: The Semgrep results — what problems were found
    top_k: How many related files to return (5 is usually enough)
    Returns: A formatted string of relevant file contents for the AI to read
    """
    collection = get_or_create_collection(repo_name)
    
    # Get the names of changed files
    changed_files = [f["filename"] for f in diff["changed_files"]]
    
    # Get the actual code that changed (the diff text)
    changed_code = "\n".join([f["patch"] for f in diff["changed_files"]])
    
    # Build a search query from what we know about this commit
    query_parts = [
        f"Files that were changed: {', '.join(changed_files)}",
        f"Code that was changed: {changed_code[:500]}",  # First 500 chars
    ]
    
    # If Semgrep found issues, include those in the query too
    if semgrep_findings:
        issues = [f["message"] for f in semgrep_findings[:3]]
        query_parts.append(f"Security issues found: {', '.join(issues)}")
    
    query = "\n".join(query_parts)
    
    try:
        # Ask ChromaDB: "What files in our index are most similar to this query?"
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),  # Don't request more than we have
            include=["documents", "metadatas", "distances"]
        )
        
        context_parts = ["=== RELATED CODEBASE CONTEXT ===\n"]
        context_parts.append("(These are files from the repo that are related to the changed code)\n")
        
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # distance < 1.5 means the file is actually related (lower = more similar)
            if distance < 1.5:
                context_parts.append(f"""
--- Related File {i+1}: {meta['file_path']} ---
{meta.get('content_preview', 'No preview available')}
""")
        
        return "\n".join(context_parts)
    
    except Exception as e:
        print(f"[RAG] Error during retrieval: {e}")
        return "No related context found."
```

### ✅ Phase 3 Test

```python
# test_phase3.py
import sys
sys.path.insert(0, ".")

from rag.indexer import index_repository
from rag.retriever import retrieve_relevant_context

# Index our test repo
print("Step 1: Indexing the test repo...")
count = index_repository("./test_repo", "test/vulnerable-app")
print(f"Indexed {count} files\n")

# Now simulate what happens when a commit comes in
print("Step 2: Retrieving relevant context for a simulated commit...")

diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": '+def get_user(username):\n+    query = f"SELECT * FROM users WHERE username = \'{username}\'"'
    }]
}
semgrep_findings = [{"message": "SQL injection in formatted query string"}]

context = retrieve_relevant_context("test/vulnerable-app", diff, semgrep_findings)
print(context)
print("✅ RAG retrieval working!")
```

```bash
python test_phase3.py
# Expected:
# Step 1: Indexing the test repo...
#   [RAG] Indexed: app.py
#   [RAG] Indexed: test_app.py
# Indexed 2 files
#
# Step 2: Retrieving relevant context...
# === RELATED CODEBASE CONTEXT ===
# --- Related File 1: app.py ---
# ...
```

---

## Phase 4 — Agent A: The Hacker (Writing the Exploit)

**What we're building:** The most important agent. Agent A reads the diff, the Semgrep findings, and the related codebase context — then writes a Python script that **proves** the vulnerability is real by actually exploiting it.

**Why prove it?** Because 40-70% of static analysis warnings are false positives. Without proof, developers ignore them. With proof ("look, I ran this script and stole your user data"), it's impossible to ignore.

```python
# agents/hacker.py

import os
from anthropic import Anthropic

# Create the Anthropic client — it automatically reads ANTHROPIC_API_KEY from .env
client = Anthropic()

# Which Claude model to use (loaded from .env)
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# The "system prompt" defines the AI's role and rules
# This is like giving the AI a job description before asking it anything
HACKER_SYSTEM_PROMPT = """You are Agent A — an expert offensive security researcher on a white-hat security team.

Your job is to analyze code changes and write a Python script that PROVES a vulnerability exists.

STRICT RULES FOR YOUR OUTPUT:
1. Write ONLY a complete, runnable Python script. No explanations before or after.
2. The script MUST print "VULNERABLE: <description>" if the exploit succeeds
3. The script MUST print "NOT_VULNERABLE" if no real vulnerability exists
4. Use exit code 0 for vulnerable, exit code 1 for not vulnerable
5. The script runs in an isolated Docker container — there is no real database
   → Create your own SQLite database in /tmp/ for testing
6. The script must be completely self-contained (include any setup it needs)
7. Only claim VULNERABLE if your script ACTUALLY demonstrates the problem
   → Do not claim vulnerabilities that are theoretical

Output ONLY the Python script. Nothing else."""


def run_hacker_agent(diff: dict, semgrep_findings: list, rag_context: str) -> dict:
    """
    Agent A analyzes the changed code and writes an exploit.
    
    Uses Claude's "extended thinking" feature — the model reasons through
    the problem step by step before writing the exploit. This produces much
    better exploits than just asking for one directly.
    
    diff: What code changed (from get_diff())
    semgrep_findings: What Semgrep found (from run_semgrep_on_files())
    rag_context: Related files from the codebase (from retrieve_relevant_context())
    Returns: The exploit script + reasoning + metadata
    """
    
    # Format the diff as readable text for Claude
    diff_text = "\n".join([
        f"=== {f['filename']} ===\n{f['patch']}\n"
        for f in diff["changed_files"]
    ])
    
    # Format Semgrep findings for Claude
    if semgrep_findings:
        semgrep_text = "\n".join([
            f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line_start']})"
            for f in semgrep_findings
        ])
    else:
        semgrep_text = "Semgrep found no specific patterns."
    
    # Build the full prompt
    user_prompt = f"""Please analyze this code change and write an exploit script.

=== WHAT CHANGED IN THIS COMMIT ===
{diff_text}

=== WHAT SEMGREP FOUND ===
{semgrep_text}

=== RELATED CODE IN THE SAME CODEBASE ===
{rag_context}

Write a complete Python exploit script that proves the most serious vulnerability.
Remember: Create a SQLite database in /tmp/ if you need database interaction."""

    print("[AGENT A] Analyzing code — this may take 15-30 seconds with extended thinking...")
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        
        # Extended thinking = Claude reasons step by step before answering
        # This is like asking someone to "show their work" before giving an answer
        # budget_tokens controls how much thinking is allowed (more = deeper reasoning)
        thinking={
            "type": "enabled",
            "budget_tokens": 2000
        },
        
        system=HACKER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # Claude's response contains two parts:
    # 1. A "thinking" block — the reasoning (we log this for debugging)
    # 2. A "text" block — the actual exploit script
    exploit_script = ""
    thinking_text = ""
    
    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking  # Claude's reasoning process
        elif block.type == "text":
            exploit_script = block.text.strip()  # The actual exploit code
    
    # Sometimes Claude wraps code in ```python ... ``` markdown fences
    # We need to remove those so we can run the script directly
    if exploit_script.startswith("```python"):
        exploit_script = exploit_script[9:]
    if exploit_script.startswith("```"):
        exploit_script = exploit_script[3:]
    if exploit_script.endswith("```"):
        exploit_script = exploit_script[:-3]
    exploit_script = exploit_script.strip()
    
    print(f"[AGENT A] Exploit generated ({len(exploit_script)} characters)")
    
    # Show a preview of Claude's reasoning (helpful for debugging)
    if thinking_text:
        print(f"[AGENT A] Claude's reasoning (preview): {thinking_text[:300]}...")
    
    return {
        "exploit_script": exploit_script,
        "reasoning": thinking_text,
        "vulnerability_type": _guess_vuln_type(semgrep_findings),
        "files_analyzed": [f["filename"] for f in diff["changed_files"]]
    }


def _guess_vuln_type(findings: list) -> str:
    """
    Make a human-readable guess at the vulnerability type based on Semgrep's rule ID.
    This is just for labeling — the AI understands the actual vulnerability.
    """
    if not findings:
        return "Unknown Vulnerability"
    
    rule_id = findings[0].get("rule_id", "").lower()
    
    if "sql" in rule_id:
        return "SQL Injection"
    elif "xss" in rule_id:
        return "Cross-Site Scripting (XSS)"
    elif "path" in rule_id or "traversal" in rule_id:
        return "Path Traversal"
    elif "injection" in rule_id:
        return "Code Injection"
    else:
        return findings[0].get("category", "Security Vulnerability")
```

### ✅ Phase 4 Test

```python
# test_phase4.py
import sys
sys.path.insert(0, ".")

from agents.hacker import run_hacker_agent

# Simulate a commit that adds a SQL injection vulnerability
diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": """+def get_user(username):
+    import sqlite3
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    # BUG: username is inserted directly — SQL injection possible
+    query = f"SELECT * FROM users WHERE username = '{username}'"
+    cursor.execute(query)
+    return cursor.fetchone()"""
    }]
}

semgrep_findings = [{
    "rule_id": "python.lang.security.audit.formatted-sql-query",
    "severity": "WARNING",
    "message": "Formatted SQL query. Possible SQL injection.",
    "line_start": 6,
    "category": "security"
}]

rag_context = "=== RELATED CODEBASE CONTEXT ===\nThis function is called by POST /login endpoint."

print("Running Agent A (The Hacker)...")
result = run_hacker_agent(diff, semgrep_findings, rag_context)

print("\n=== GENERATED EXPLOIT SCRIPT ===")
print(result["exploit_script"])
print(f"\nVulnerability type: {result['vulnerability_type']}")
```

```bash
python test_phase4.py
# Expected: Claude generates a Python script that:
# - Creates a SQLite DB with test data
# - Tries a SQL injection like: ' OR '1'='1
# - Prints "VULNERABLE: SQL Injection confirmed..." if it works
```

---

## Phase 5 — Running the Exploit Safely in Docker

**What we're building:** A function that takes the exploit script from Agent A and runs it inside a locked-down Docker container. We capture the output to see if the exploit succeeded.

**Why this is critical:** Never run untrusted code directly on your server. The exploit script is designed to attack things. Docker is our quarantine chamber.

```python
# sandbox/docker_runner.py

import docker      # Python library to control Docker
import tempfile    # For creating temporary folders
import os

# Connect to Docker running on this machine
docker_client = docker.from_env()

# We use the official Python image as our sandbox base
SANDBOX_IMAGE = "python:3.11-slim"


def run_exploit_in_sandbox(exploit_script: str, repo_path: str, timeout: int = 30) -> dict:
    """
    Run an exploit script in a completely isolated Docker container.
    
    Safety guarantees:
    - No internet access (network_mode="none")
    - Limited RAM (256MB max)
    - Limited CPU (50% of one core)
    - Container is destroyed immediately after running
    - Even if the exploit does something destructive, it can't escape
    
    exploit_script: The Python code written by Agent A
    repo_path: Path to the local repo (mounted as read-only inside container)
    timeout: Max seconds to wait before killing the container
    Returns: Dict with exit code, output, and whether the exploit succeeded
    """
    
    print("[DOCKER] Starting isolated sandbox container...")
    
    # We use a temporary folder to pass the exploit script to the container
    with tempfile.TemporaryDirectory() as tmpdir:
        
        # Write the exploit script to a file in the temp folder
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(exploit_script)
        
        try:
            # Create and start the Docker container
            container = docker_client.containers.run(
                SANDBOX_IMAGE,                  # Use Python 3.11 slim image
                
                # Mount two folders into the container:
                volumes={
                    tmpdir: {
                        "bind": "/sandbox",  # exploit.py lives here
                        "mode": "ro"         # read-only — container can't modify it
                    },
                    repo_path: {
                        "bind": "/app",      # the repo code lives here
                        "mode": "ro"         # read-only
                    },
                },
                
                working_dir="/app",          # Start in the repo folder
                
                # === SECURITY RESTRICTIONS ===
                network_mode="none",         # No internet — can't call home or leak data
                mem_limit="256m",            # Can't use more than 256MB RAM
                cpu_quota=50000,             # Can only use 50% of one CPU
                read_only=False,             # App may need to write temp files
                tmpfs={"/tmp": "size=64m"},  # Only allowed to write to /tmp (64MB max)
                # ================================
                
                remove=False,    # Don't auto-remove — we need to read logs first
                detach=True,     # Run in background so we can add a timeout
                
                # Command to run: execute our exploit script
                entrypoint=["python", "/sandbox/exploit.py"]
            )
            
            try:
                # Wait for the container to finish (with a timeout)
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                
                # Read what the script printed to stdout and stderr
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
                
            except Exception as e:
                # Container timed out or crashed
                exit_code = -1
                stdout = ""
                stderr = f"Container timed out or crashed: {e}"
            
            finally:
                # ALWAYS destroy the container — no matter what happened
                # This is the most important line in this function
                try:
                    container.remove(force=True)
                    print("[DOCKER] Container destroyed. Nothing persists.")
                except:
                    pass  # Container might already be gone — that's fine
            
            # The exploit succeeded if:
            # 1. The script exited with code 0 (success)
            # 2. The output contains "VULNERABLE"
            # 3. The output does NOT contain "NOT_VULNERABLE"
            exploit_succeeded = (
                exit_code == 0 and
                "VULNERABLE" in stdout and
                "NOT_VULNERABLE" not in stdout
            )
            
            print(f"[DOCKER] Exit code: {exit_code}")
            print(f"[DOCKER] Vulnerability confirmed: {exploit_succeeded}")
            if stdout:
                print(f"[DOCKER] Output: {stdout[:200]}")
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "exploit_succeeded": exploit_succeeded,
                "vulnerability_confirmed": exploit_succeeded,
                "output_summary": stdout[:500] if stdout else stderr[:500]
            }
        
        except docker.errors.DockerException as e:
            # Docker itself failed — maybe Docker isn't running?
            print(f"[DOCKER] Docker error: {e}")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": f"Docker error: {e}"
            }


def run_tests_in_sandbox(repo_path: str, timeout: int = 60) -> dict:
    """
    Run the repo's unit tests inside a sandboxed container.
    
    We use this in Phase 7 to verify that Agent B's patch doesn't break anything.
    
    repo_path: The path to the repo (with the patch already applied)
    Returns: Whether tests passed, and the full test output
    """
    print("[DOCKER] Running test suite in sandbox...")
    
    try:
        container = docker_client.containers.run(
            SANDBOX_IMAGE,
            # Install pytest, then run all tests
            command="sh -c 'pip install pytest -q && python -m pytest /app -v 2>&1'",
            volumes={repo_path: {"bind": "/app", "mode": "ro"}},
            working_dir="/app",
            network_mode="none",
            mem_limit="512m",   # Tests may need more memory than exploits
            remove=False,
            detach=True
        )
        
        result = container.wait(timeout=timeout)
        logs = container.logs().decode("utf-8")
        
        try:
            container.remove(force=True)
        except:
            pass
        
        tests_passed = result["StatusCode"] == 0
        print(f"[DOCKER] Tests: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
        
        return {
            "tests_passed": tests_passed,
            "exit_code": result["StatusCode"],
            "output": logs
        }
    
    except Exception as e:
        return {
            "tests_passed": False,
            "exit_code": -1,
            "output": f"Error running tests: {e}"
        }
```

### ✅ Phase 5 Test

```python
# test_phase5.py
import sys
sys.path.insert(0, ".")

from sandbox.docker_runner import run_exploit_in_sandbox

# A simple exploit script we know should succeed
# This creates a test database and demonstrates SQL injection
test_exploit_script = """
import sqlite3
import os

# Step 1: Create a test database with fake user data
conn = sqlite3.connect("/tmp/test.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)")
cursor.execute("INSERT INTO users VALUES (1, 'admin', 'secret_password')")
cursor.execute("INSERT INTO users VALUES (2, 'alice', 'alice_password')")
conn.commit()

# Step 2: Try the SQL injection attack
# A normal request: username = "admin"  → only returns the admin row
# An attack:        username = "' OR '1'='1"  → returns ALL rows (data leak!)
malicious_input = "' OR '1'='1"

query = f"SELECT * FROM users WHERE username = '{malicious_input}'"
print(f"Executing query: {query}")

cursor.execute(query)
results = cursor.fetchall()

# Step 3: Report the result
if len(results) > 1:
    # We got more rows than we should have — injection worked!
    print(f"VULNERABLE: SQL Injection confirmed!")
    print(f"Leaked {len(results)} rows of user data: {results}")
    exit(0)
else:
    print("NOT_VULNERABLE: Query returned expected number of rows")
    exit(1)
"""

print("Testing Docker sandbox execution...")
print("(Make sure Docker Desktop is running first!)\n")

result = run_exploit_in_sandbox(test_exploit_script, "/tmp")

print(f"\nFull result:")
print(f"  Exit code: {result['exit_code']}")
print(f"  Exploit worked: {result['exploit_succeeded']}")
print(f"  Output: {result['stdout']}")
```

```bash
# First, make sure Docker is running:
docker ps   # Should show something, not an error

python test_phase5.py
# Expected:
# [DOCKER] Starting isolated sandbox container...
# [DOCKER] Exit code: 0
# [DOCKER] Vulnerability confirmed: True
# [DOCKER] Container destroyed. Nothing persists.
# Exploit worked: True
```

---

## Phase 6 — Agent B: The Engineer (Writing the Fix)

**What we're building:** Agent B receives the vulnerable code + proof of exploit, and rewrites the vulnerable function to be safe. The key constraint: the fix must not change how the function behaves for normal, valid inputs.

```python
# agents/engineer.py

import os
from anthropic import Anthropic

client = Anthropic()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

ENGINEER_SYSTEM_PROMPT = """You are Agent B — a senior security engineer who writes clean, safe code.

You've been shown a vulnerability and proof that it's exploitable. Fix it.

RULES:
1. Fix ONLY the security vulnerability. Don't refactor anything unrelated.
2. Keep the exact same function signatures — other code calls these functions
3. For SQL injection: use parameterized queries (cursor.execute(sql, params))
4. For other issues: use the safest standard approach for that language
5. Output ONLY the complete, fixed Python code for the file. Nothing else.
6. Do not add comments like "# Fixed SQL injection" — write clean, professional code"""


def run_engineer_agent(
    vulnerable_code: str,
    file_path: str,
    exploit_output: str,
    vulnerability_type: str,
    error_logs: str = None   # Only provided when Agent C rejected the last attempt
) -> dict:
    """
    Agent B writes a patch for the vulnerability.
    
    vulnerable_code: The current broken code (the full file contents)
    file_path: Which file needs to be changed (e.g., "app.py")
    exploit_output: What Agent A's exploit printed — proof of the problem
    vulnerability_type: Human-readable label (e.g., "SQL Injection")
    error_logs: If Agent C rejected a previous patch, what went wrong
    Returns: The patched file contents
    """
    
    # If a previous patch was rejected, tell Agent B exactly what went wrong
    retry_context = ""
    if error_logs:
        retry_context = f"""
⚠️  YOUR PREVIOUS PATCH WAS REJECTED. Here is what failed:
{error_logs}

Please fix these issues in your new patch attempt."""
    
    user_prompt = f"""Fix the security vulnerability in {file_path}.

=== VULNERABILITY TYPE ===
{vulnerability_type}

=== CURRENT VULNERABLE CODE ===
{vulnerable_code}

=== PROOF THAT THE VULNERABILITY IS REAL (exploit output) ===
{exploit_output}

{retry_context}

Output ONLY the complete, fixed Python code for {file_path}. No explanation. Just the code."""
    
    print(f"[AGENT B] Writing patch for {file_path}...")
    if error_logs:
        print("[AGENT B] This is a retry — incorporating feedback from previous failure")
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=ENGINEER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    patched_code = response.content[0].text.strip()
    
    # Remove markdown code fences if Claude added them
    if patched_code.startswith("```python"):
        patched_code = patched_code[9:]
    if patched_code.startswith("```"):
        patched_code = patched_code[3:]
    if patched_code.endswith("```"):
        patched_code = patched_code[:-3]
    patched_code = patched_code.strip()
    
    print(f"[AGENT B] Patch ready ({len(patched_code)} characters)")
    
    return {
        "file_path": file_path,
        "patched_code": patched_code,
        "is_retry": error_logs is not None
    }
```

### ✅ Phase 6 Test

```python
# test_phase6.py
import sys
sys.path.insert(0, ".")

from agents.engineer import run_engineer_agent

vulnerable_code = """import sqlite3

def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
"""

exploit_output = """
VULNERABLE: SQL Injection confirmed!
Input used: ' OR '1'='1
Query that ran: SELECT * FROM users WHERE username = '' OR '1'='1'
Leaked 2 rows of user data: [(1, 'admin', 'secret'), (2, 'alice', 'pass')]
"""

result = run_engineer_agent(
    vulnerable_code=vulnerable_code,
    file_path="app.py",
    exploit_output=exploit_output,
    vulnerability_type="SQL Injection"
)

print("=== PATCHED CODE ===")
print(result["patched_code"])

# A properly patched SQL query uses ? placeholders, not f-strings
if "?" in result["patched_code"] or "%s" in result["patched_code"]:
    print("\n✅ Patch correctly uses parameterized queries!")
else:
    print("\n⚠️  Warning: Patch might not be using parameterized queries")
```

```bash
python test_phase6.py
# Expected: The patched code should look something like:
#   cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
# Instead of:
#   cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

---

## Phase 7 — Agent C: The Reviewer + Retry Loop

**What we're building:** The quality gate. Agent C runs two checks on the patched code:
1. **Do all existing unit tests still pass?** (We didn't break anything)
2. **Does the original exploit now FAIL?** (The vulnerability is actually fixed)

If either check fails, Agent C sends the error report back to Agent B for another attempt. Maximum 3 tries.

```python
# agents/reviewer.py

import os
import shutil
import tempfile
from anthropic import Anthropic
from sandbox.docker_runner import run_tests_in_sandbox, run_exploit_in_sandbox

client = Anthropic()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# If Agent B can't fix it in 3 tries, we escalate to a human
MAX_RETRIES = 3


def run_reviewer_agent(
    original_code: str,
    patched_code: str,
    exploit_script: str,
    repo_path: str,
    file_path: str
) -> dict:
    """
    Verify that a patch is actually correct.
    
    Two checks must BOTH pass:
    ✅ All unit tests pass on the patched code
    ✅ The original exploit script now prints NOT_VULNERABLE
    
    original_code: The broken code (before patch)
    patched_code: The fixed code (Agent B's output)
    exploit_script: The attack script (Agent A's output)
    repo_path: The local repo path
    file_path: Which file was patched (e.g., "app.py")
    Returns: Whether the patch was approved, and error details if not
    """
    
    # Create a copy of the repo with the patch applied
    # We don't want to modify the original repo during testing
    patched_repo = tempfile.mkdtemp()
    shutil.copytree(repo_path, patched_repo, dirs_exist_ok=True)
    
    # Write the patched file into our copy
    patched_file_path = os.path.join(patched_repo, file_path)
    os.makedirs(os.path.dirname(patched_file_path), exist_ok=True)
    with open(patched_file_path, "w") as f:
        f.write(patched_code)
    
    print("[AGENT C] Check 1: Running test suite on patched code...")
    test_result = run_tests_in_sandbox(patched_repo)
    
    print("[AGENT C] Check 2: Running exploit on patched code (should fail now)...")
    exploit_result = run_exploit_in_sandbox(exploit_script, patched_repo)
    
    # Clean up the temporary copy
    shutil.rmtree(patched_repo, ignore_errors=True)
    
    tests_passed = test_result["tests_passed"]
    
    # The exploit should NO LONGER work — if it does, the patch failed
    exploit_still_works = exploit_result["exploit_succeeded"]
    
    # Both conditions must be true for approval
    patch_approved = tests_passed and not exploit_still_works
    
    # Build an error report for Agent B if the patch was rejected
    error_report = None
    if not patch_approved:
        errors = []
        
        if not tests_passed:
            errors.append(
                f"❌ TESTS FAILED — your patch broke existing functionality:\n"
                f"{test_result['output'][-1000:]}"  # Last 1000 chars of test output
            )
        
        if exploit_still_works:
            errors.append(
                f"❌ EXPLOIT STILL WORKS — the vulnerability was not fixed:\n"
                f"{exploit_result['stdout']}"
            )
        
        error_report = "\n\n".join(errors)
    
    status = "✅ APPROVED" if patch_approved else "❌ REJECTED"
    print(f"[AGENT C] Review verdict: {status}")
    if error_report:
        print(f"[AGENT C] Reason for rejection: {error_report[:200]}")
    
    return {
        "approved": patch_approved,
        "tests_passed": tests_passed,
        "exploit_blocked": not exploit_still_works,
        "error_report": error_report,
        "test_output": test_result["output"],
        "exploit_output": exploit_result["stdout"]
    }


def full_remediation_loop(
    diff: dict,
    semgrep_findings: list,
    rag_context: str,
    repo_path: str
) -> dict:
    """
    The complete Aegis pipeline: Agent A → Docker → Agent B → Agent C → loop.
    
    This is the heart of Aegis. It:
    1. Asks Agent A to write an exploit
    2. Runs the exploit to confirm the vulnerability is real
    3. Asks Agent B to write a patch (up to 3 times)
    4. Asks Agent C to verify the patch works each time
    5. Returns the final result (patched or needs human review)
    
    Returns a dict with status "PATCHED", "NO_VULNERABILITY", or "FAILED_TO_PATCH"
    """
    from agents.hacker import run_hacker_agent
    from agents.engineer import run_engineer_agent
    
    print("\n" + "="*50)
    print("STEP 1: Agent A writing exploit...")
    print("="*50)
    hack_result = run_hacker_agent(diff, semgrep_findings, rag_context)
    exploit_script = hack_result["exploit_script"]
    
    print("\n" + "="*50)
    print("STEP 2: Testing if exploit actually works...")
    print("="*50)
    exploit_test = run_exploit_in_sandbox(exploit_script, repo_path)
    
    if not exploit_test["exploit_succeeded"]:
        # Semgrep flagged it but the AI couldn't actually exploit it
        # This is a false positive — no real vulnerability
        print("\n[ORCHESTRATOR] Exploit didn't succeed → False positive. No action needed.")
        return {
            "status": "NO_VULNERABILITY",
            "message": "Semgrep flagged a pattern, but no actual exploit could be demonstrated.",
            "exploit_output": exploit_test["stdout"]
        }
    
    print(f"\n[ORCHESTRATOR] 🚨 VULNERABILITY CONFIRMED: {hack_result['vulnerability_type']}")
    
    # Read the current contents of the vulnerable file
    changed_file = diff["changed_files"][0]["filename"]
    try:
        with open(os.path.join(repo_path, changed_file)) as f:
            vulnerable_code = f.read()
    except FileNotFoundError:
        # If we can't read the file, use the diff text as a fallback
        vulnerable_code = "\n".join([f["patch"] for f in diff["changed_files"]])
    
    error_logs = None   # No errors on the first attempt
    final_patch = None  # We'll set this when a patch is approved
    
    print("\n" + "="*50)
    print("STEP 3: Agent B + C patch-and-verify loop...")
    print("="*50)
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n--- Patch attempt {attempt} of {MAX_RETRIES} ---")
        
        # Agent B writes a patch (with error feedback if this is a retry)
        patch_result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path=changed_file,
            exploit_output=exploit_test["stdout"],
            vulnerability_type=hack_result["vulnerability_type"],
            error_logs=error_logs  # None on first attempt, error details on retries
        )
        
        # Agent C checks if the patch is correct
        review_result = run_reviewer_agent(
            original_code=vulnerable_code,
            patched_code=patch_result["patched_code"],
            exploit_script=exploit_script,
            repo_path=repo_path,
            file_path=changed_file
        )
        
        if review_result["approved"]:
            print(f"\n[ORCHESTRATOR] ✅ Patch approved on attempt {attempt}!")
            final_patch = patch_result
            break
        else:
            # Patch was rejected — pass the error details to Agent B for the next attempt
            error_logs = review_result["error_report"]
            print(f"\n[ORCHESTRATOR] Attempt {attempt} failed. {'Retrying...' if attempt < MAX_RETRIES else 'Out of retries.'}")
    
    # Return the final result
    if final_patch:
        return {
            "status": "PATCHED",
            "file": changed_file,
            "vulnerability_type": hack_result["vulnerability_type"],
            "patched_code": final_patch["patched_code"],
            "exploit_script": exploit_script,
            "exploit_output": exploit_test["stdout"],
            "reasoning": hack_result["reasoning"],
            "attempts": attempt
        }
    else:
        # All 3 attempts failed — a human needs to look at this
        return {
            "status": "FAILED_TO_PATCH",
            "vulnerability_type": hack_result["vulnerability_type"],
            "exploit_script": exploit_script,
            "exploit_output": exploit_test["stdout"],
            "error": f"Could not auto-patch after {MAX_RETRIES} attempts. Needs human review.",
            "last_error": error_logs
        }
```

---

## Phase 8 — Creating the Pull Request

**What we're building:** The final output. Once a good patch is found, we create a GitHub Pull Request with all the evidence. The developer reviews it, sees the proof, and can merge with confidence.

```python
# github/pr_creator.py

import os
from github import Github
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def create_security_pr(repo_name: str, result: dict, base_branch: str = "main") -> str:
    """
    Create a GitHub Pull Request with the security patch.
    
    The PR includes:
    - A clear title explaining what vulnerability was fixed
    - The exploit output (proof the vulnerability was real)
    - Confirmation that tests pass and exploit is blocked
    - A description of how Aegis found and fixed it
    
    repo_name: e.g., "alice/my-app"
    result: The dict returned by full_remediation_loop() with status "PATCHED"
    base_branch: The branch to merge into (usually "main")
    Returns: The URL of the created PR
    """
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    
    # Create a unique branch name for this fix
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    vuln_slug = result['vulnerability_type'].lower().replace(' ', '-').replace('(', '').replace(')', '')
    branch_name = f"aegis/fix-{vuln_slug}-{timestamp}"
    
    print(f"[PR] Creating branch: {branch_name}")
    
    # Get the SHA of the latest commit on the base branch
    base_sha = repo.get_branch(base_branch).commit.sha
    
    # Create the new branch from that SHA
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    
    # Update the vulnerable file with the patched code on the new branch
    file_path = result["file"]
    try:
        existing_file = repo.get_contents(file_path, ref=base_branch)
        repo.update_file(
            path=file_path,
            message=f"fix(security): patch {result['vulnerability_type']} in {file_path}",
            content=result["patched_code"],
            sha=existing_file.sha,  # Required by GitHub API when updating existing files
            branch=branch_name
        )
    except Exception as e:
        print(f"[PR] Failed to update file on GitHub: {e}")
        return None
    
    # Build the PR description — this is what the developer sees when reviewing
    vuln_type = result['vulnerability_type']
    file_name = result['file']
    exploit_preview = result['exploit_output'][:600]
    attempts = result.get('attempts', 1)
    
    pr_body = f"""## 🛡️ Aegis Automated Security Fix

**Vulnerability Type:** {vuln_type}
**File Patched:** `{file_name}`
**Patch attempts needed:** {attempts}

---

### 🔴 This vulnerability was PROVEN real, not just flagged

The following exploit script was run in an isolated Docker container and confirmed the vulnerability:

```
{exploit_preview}
```

---

### ✅ Verification Results

| Check | Result |
|-------|--------|
| Existing unit tests pass on patched code | ✅ Pass |
| Original exploit fails on patched code | ✅ Blocked |

---

### 🤖 How Aegis Found and Fixed This

1. **Semgrep** detected a suspicious pattern on your commit
2. **Agent A (The Hacker)** wrote a targeted exploit and proved the vulnerability is real
3. **Agent B (The Engineer)** wrote a minimal patch fixing only the vulnerability
4. **Agent C (The Reviewer)** ran tests and confirmed the exploit is blocked

---

> ⚠️ **Please review this patch before merging.** Aegis is automated but you should verify the fix makes sense for your codebase.

---
*Auto-generated by [Aegis](https://github.com/your-org/aegis) — Autonomous White-Hat Security System*"""

    # Create the Pull Request
    pr = repo.create_pull(
        title=f"[Aegis] Fix {vuln_type} in {file_name}",
        body=pr_body,
        head=branch_name,
        base=base_branch
    )
    
    print(f"[PR] ✅ Pull Request created: {pr.html_url}")
    return pr.html_url
```

---

## Phase 9 — Connecting Everything Together

**What we're building:** The final orchestrator that connects all phases into one pipeline, and wiring it into the webhook so it runs automatically on every push.

### Step 9.1 — The orchestrator

```python
# orchestrator.py

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from github.diff_fetcher import get_diff, clone_or_pull_repo
from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm
from rag.indexer import index_repository
from rag.retriever import retrieve_relevant_context
from agents.reviewer import full_remediation_loop
from github.pr_creator import create_security_pr

# Where to store cloned repos on our server
REPOS_DIR = "./repos"
os.makedirs(REPOS_DIR, exist_ok=True)

# Track which repos we've already indexed so we don't re-index every time
indexed_repos = set()


async def run_aegis_pipeline(push_info: dict):
    """
    The complete Aegis pipeline. Triggered on every push.
    
    push_info: The dict from extract_push_info() in Phase 1
    
    The pipeline:
    1. Clone/update the repo locally
    2. Index it (if first time) for RAG
    3. Get the diff (what changed?)
    4. Run Semgrep (any suspicious patterns?)
    5. Get relevant context from RAG
    6. Run the full agent loop (hack → patch → verify)
    7. Create a PR if a good patch was found
    """
    
    repo_name = push_info["repo_name"]
    commit_sha = push_info["commit_sha"]
    
    print(f"\n{'='*60}")
    print(f"[AEGIS] New pipeline: {repo_name} @ {commit_sha[:8]}")
    print(f"[AEGIS] Branch: {push_info['branch']}")
    print(f"[AEGIS] Message: {push_info['commit_message'][:60]}")
    print(f"{'='*60}\n")
    
    # Step 1: Get the code onto our server
    # Repo folder name: replace / with _ to avoid filesystem issues
    repo_path = os.path.join(REPOS_DIR, repo_name.replace("/", "_"))
    clone_or_pull_repo(push_info["repo_url"], repo_path)
    
    # Step 2: Index the repo the first time we see it
    if repo_name not in indexed_repos:
        print(f"[AEGIS] First time seeing {repo_name} — building search index...")
        index_repository(repo_path, repo_name)
        indexed_repos.add(repo_name)
        print(f"[AEGIS] Index complete!\n")
    
    # Step 3: Get what changed in this commit
    diff = get_diff(repo_name, commit_sha)
    
    if not diff["changed_files"]:
        print("[AEGIS] No code files changed in this commit. Skipping analysis.")
        return
    
    print(f"[AEGIS] Code files changed: {[f['filename'] for f in diff['changed_files']]}")
    
    # Step 4: Quick scan with Semgrep first (fast, free)
    changed_file_paths = [f["filename"] for f in diff["changed_files"]]
    semgrep_findings = run_semgrep_on_files(changed_file_paths, repo_path)
    
    if not semgrep_findings:
        print("[AEGIS] ✅ Semgrep found nothing suspicious. Skipping AI analysis.")
        print("[AEGIS] Pipeline complete — no action needed.\n")
        return
    
    print(f"[AEGIS] Semgrep found {len(semgrep_findings)} suspicious pattern(s)")
    print("[AEGIS] Activating AI agents...\n")
    
    # Step 5: Get relevant codebase context via RAG
    rag_context = retrieve_relevant_context(repo_name, diff, semgrep_findings)
    
    # Step 6: Run the full hack → patch → verify loop
    result = full_remediation_loop(diff, semgrep_findings, rag_context, repo_path)
    
    print(f"\n[AEGIS] Pipeline result: {result['status']}")
    
    # Step 7: Take action based on the result
    if result["status"] == "PATCHED":
        # Great! We found a real vulnerability and fixed it. Open a PR.
        pr_url = create_security_pr(repo_name, result)
        print(f"[AEGIS] ✅ Done! PR created: {pr_url}\n")
    
    elif result["status"] == "FAILED_TO_PATCH":
        # Real vulnerability but our agents couldn't fix it. Alert a human.
        print(f"[AEGIS] ⚠️  Vulnerability found but couldn't auto-patch.")
        print(f"[AEGIS] Vulnerability: {result['vulnerability_type']}")
        print(f"[AEGIS] Manual review needed.\n")
        # TODO: Send Slack alert or create a "needs human review" issue
    
    else:
        # Semgrep flagged it but it wasn't actually exploitable
        print(f"[AEGIS] ℹ️  False positive — no real vulnerability confirmed.\n")
```

### Step 9.2 — Wire the orchestrator into the webhook

Update `main.py` to uncomment the background task line:

```python
# main.py — update the webhook handler
# Find this line in main.py:

    # background_tasks.add_task(run_aegis_pipeline, push_info)
    # ↑ We'll uncomment this in Phase 9 once we've built everything

# Change it to this:

    from orchestrator import run_aegis_pipeline
    background_tasks.add_task(run_aegis_pipeline, push_info)
```

### ✅ Phase 9 — Full End-to-End Test

```bash
# Terminal 1: Start Aegis
python main.py

# Terminal 2: Start ngrok (so GitHub can reach you)
ngrok http 8000

# Terminal 3: Add a new vulnerability to the test repo and push it
cd test_repo
cat >> app.py << 'EOF'

# New vulnerable function
def find_product(name):
    import sqlite3
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE name = '{name}'")
    return cursor.fetchall()
EOF

git add .
git commit -m "Add product search feature"
git push
```

**Watch Terminal 1 — you should see the full pipeline run:**

```
============================================================
[AEGIS] New pipeline: yourname/test-repo @ abc12345
[AEGIS] Branch: main
[AEGIS] Message: Add product search feature
============================================================

[AEGIS] Code files changed: ['app.py']
[AEGIS] Semgrep found 1 suspicious pattern(s)
[AEGIS] Activating AI agents...

==================================================
STEP 1: Agent A writing exploit...
==================================================
[AGENT A] Analyzing code — this may take 15-30 seconds with extended thinking...
[AGENT A] Exploit generated (847 characters)

==================================================
STEP 2: Testing if exploit actually works...
==================================================
[DOCKER] Starting isolated sandbox container...
[DOCKER] Exit code: 0
[DOCKER] Vulnerability confirmed: True
[DOCKER] Container destroyed. Nothing persists.

[ORCHESTRATOR] 🚨 VULNERABILITY CONFIRMED: SQL Injection

==================================================
STEP 3: Agent B + C patch-and-verify loop...
==================================================

--- Patch attempt 1 of 3 ---
[AGENT B] Writing patch for app.py...
[AGENT C] Check 1: Running test suite on patched code...
[DOCKER] Tests: ✅ PASSED
[AGENT C] Check 2: Running exploit on patched code (should fail now)...
[DOCKER] Vulnerability confirmed: False
[AGENT C] Review verdict: ✅ APPROVED

[ORCHESTRATOR] ✅ Patch approved on attempt 1!

[AEGIS] Pipeline result: PATCHED
[PR] Creating branch: aegis/fix-sql-injection-20260422-143055
[PR] ✅ Pull Request created: https://github.com/yourname/test-repo/pull/1

[AEGIS] ✅ Done! PR created: https://github.com/yourname/test-repo/pull/1
```

**Open the PR link in your browser — you should see the exploit proof and the fix.**

---

## 🗂️ Final Project Structure

```
Aegis/
├── docs/                         # Existing documentation
│   ├── about.md
│   ├── Phases.md
│   └── context.md
├── main.py                       # FastAPI entry point
├── orchestrator.py               # Pipeline coordinator
├── config.py                     # Centralized configuration
├── agents/
│   ├── __init__.py
│   ├── hacker.py                 # Agent A — exploit writer
│   ├── engineer.py               # Agent B — patch writer
│   └── reviewer.py               # Agent C — verifier + retry loop
├── rag/
│   ├── __init__.py
│   ├── indexer.py                # One-time repo indexing
│   └── retriever.py              # Per-commit context retrieval
├── sandbox/
│   ├── __init__.py
│   └── docker_runner.py          # Isolated Docker execution
├── github/
│   ├── __init__.py
│   ├── webhook.py                # Webhook validation + parsing
│   ├── diff_fetcher.py           # Git diff retrieval
│   └── pr_creator.py             # PR creation
├── scanner/
│   ├── __init__.py
│   └── semgrep_runner.py         # Semgrep integration
├── test_repo/                    # Intentionally vulnerable demo repo
│   ├── app.py
│   └── test_app.py
├── tests/                        # Phase verification tests
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_phase5.py
│   └── test_phase6.py
```

---

## 🛠️ Quick Commands Cheat Sheet

```bash
# === Every time you open a new terminal ===
cd aegis
source venv/bin/activate         # Activate the virtual environment

# === Starting Aegis ===
python main.py                   # Start the web server on port 8000

# === Exposing to the internet (for GitHub webhooks) ===
ngrok http 8000                  # Creates a public URL

# === Testing each phase individually ===
python test_phase2.py            # Test Semgrep scanner
python test_phase3.py            # Test RAG indexer and retriever
python test_phase4.py            # Test Agent A (exploit writer)
python test_phase5.py            # Test Docker sandbox
python test_phase6.py            # Test Agent B (patch writer)

# === Useful debugging commands ===
curl http://localhost:8000/health                    # Is the server running?
docker ps                                            # Is Docker running?
semgrep --version                                    # Is Semgrep installed?
python -c "import anthropic; print('API OK')"       # Can we reach Claude?

# === If you need to re-index a repo ===
python -c "
from rag.indexer import index_repository
index_repository('./repos/your_repo_name', 'user/repo')
"
```

---

## 🐛 Troubleshooting Common Problems

**"Invalid signature" from webhook**
→ The `GITHUB_WEBHOOK_SECRET` in your `.env` doesn't match what you typed into GitHub's webhook settings. They must be identical.

**"Docker error: Cannot connect to the Docker daemon"**
→ Docker Desktop isn't running. Start it first, then retry.

**Agent A generates an exploit but it doesn't print "VULNERABLE"**
→ The format matters exactly. The script must print the literal string "VULNERABLE" (all caps). Check the exploit script Agent A generated.

**Semgrep finds nothing on a file you know is vulnerable**
→ Try running Semgrep manually: `semgrep --config auto test_repo/app.py --json`
→ Make sure the file is saved and the path is correct.

**ChromaDB error "collection not found"**
→ You need to index the repo first. Run `python test_phase3.py` to build the index.

**ngrok URL keeps changing**
→ Free ngrok URLs change every time you restart. Update the GitHub webhook URL each time, or get a paid ngrok account for a stable URL.

---

*Build one phase at a time. Run the test at the end of each phase before moving to the next. If a test fails, fix it before moving on — everything connects to everything else.*
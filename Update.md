# Aegis — Deep Analysis, Gap Assessment & Levelling-Up Blueprint

> **Prepared after full review of the codebase documentation, problem statement, and current industry research on autonomous security systems, multi-agent architectures, and production AI best practices.**

---

## TL;DR — What's Actually Wrong

| Category | Severity | Summary |
|---|---|---|
| Agent 4 (Verifier) is not an LLM | 🔴 Critical | The problem statement requires an intelligent reviewer agent. Current impl is raw Python logic — no reasoning, no root-cause diagnosis. |
| Structured outputs not enforced | 🔴 Critical | JSON is parsed with regex fallback. This is a reliability time bomb at scale. |
| Only first confirmed vuln is fixed | 🔴 Critical | Multi-vulnerability commits get partial remediation silently. |
| GitHub tokens stored in plaintext | 🔴 Critical | Catastrophic if DB is leaked. |
| Subprocess fallback in sandbox | 🔴 Critical | Dev convenience that will run in production — no isolation, real damage possible. |
| ML & Threat Engine are placeholders | 🟠 High | Sold as intelligence features, built as heuristics from repo name keywords. Completely misleading. |
| SSE polling every 1 second against DB | 🟠 High | Does not scale. 10 users = 600 DB reads/minute for nothing. |
| No database migrations (Alembic) | 🟠 High | Schema change → delete DB and restart. Production-incompatible. |
| Auth stored in localStorage | 🟠 High | XSS vulnerability. Any injected script can steal user's GitHub token. |
| RAG uses DefaultEmbeddingFunction | 🟡 Medium | ChromaDB default is a weak all-MiniLM model. Purpose-built code embedding models exist. |
| No API versioning or rate limiting | 🟡 Medium | No `/v1/` prefix, no throttle — any abuse kills the service. |
| No pagination on list endpoints | 🟡 Medium | 1000 scans? Full table returned. |
| No human-in-the-loop for CRITICAL | 🟡 Medium | Automatically opens PRs for CRITICAL-severity vulns without any approval gate. |
| No CVSS scoring | 🟡 Medium | Severity is a string from the LLM, not a standardized score. |
| Frontend has no error boundaries | 🟡 Medium | Any unhandled error crashes the full page. |

---

## 1. The Problem Statement vs. What Was Built

### What the Problem Statement Actually Asks For

```
Agent A (Hacker)    → Analyze code, write exploit script, test if vulnerability exists
Agent B (Engineer)  → If exploit succeeds, rewrite vulnerable code to patch it (without breaking existing functionality)
Agent C (Reviewer)  → Run unit tests AND exploit against patched code; if it fails, send back to B WITH error logs
```

### What Aegis Actually Built

```
Agent 1 (Finder)    → ✅ Good addition — not in spec but genuinely useful
Agent 2 (Exploiter) → ✅ Maps to Agent A — well designed
Agent 3 (Engineer)  → ✅ Maps to Agent B — good model choice (Devstral)
Agent 4 (Verifier)  → ⚠️ Supposed to map to Agent C, but is pure Python loop logic, NOT an LLM agent
```

### The Gap: Agent C / Verifier is Not Intelligent

The problem statement explicitly wants an **agent** that reviews failures. A real Agent C would:
- Look at the failing test output and *reason* about WHY it failed
- Distinguish between "test is wrong" vs "patch is incomplete" vs "exploit vector changed"
- Generate a natural-language summary for the engineer explaining the specific failure mode
- Potentially suggest which part of the patch to re-examine

Currently `reviewer.py` just passes `error_logs` mechanically. There's no reasoning about what went wrong. The Engineer gets a raw pytest traceback and has to figure it out cold. This is the biggest architectural violation of the problem statement.

**Fix**: Turn Verifier into a real LLM agent with a dedicated role:

```python
# What reviewer.py SHOULD do (conceptually):
class ReviewerAgent:
    """
    Analyzes test failures and exploit results to produce 
    a structured, reasoned diagnosis for the Engineer.
    """
    def diagnose_failure(
        self,
        original_vuln: VulnerabilityFinding,
        patched_code: str,
        test_output: str,
        exploit_output: str,
        attempt_number: int
    ) -> ReviewerDiagnosis:
        # LLM reasons about the failure
        # Returns structured: root_cause, what_to_fix, confidence, suggested_approach
        ...

class ReviewerDiagnosis(BaseModel):
    root_cause: str          # "Patch only sanitizes GET params, POST body still unfiltered"
    what_to_fix: str         # Specific instruction for Engineer
    confidence: str          # HIGH | MEDIUM | LOW
    test_issues: list[str]   # Specific test failures explained
    exploit_still_works: bool
    suggested_approach: str  # "Use a whitelist validator on ALL request inputs"
```

---

## 2. Critical Bugs

### Bug 1: JSON Parsing with Regex Fallback = Reliability Time Bomb

**Current code pattern (finder.py, exploiter.py, engineer.py)**:
```python
# Tries JSON parse → falls back to regex → silently corrupts output
try:
    result = json.loads(response_text)
except:
    # regex fallback
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    result = json.loads(match.group())
```

**Why it's dangerous**: The regex fallback will silently extract *partial* JSON from a malformed response. You'll get a `VulnerabilityFinding` that has wrong line numbers or truncated descriptions — no exception is raised, and the corrupted data flows into your DB and eventually a PR.

**Fix**: Use Groq's/Mistral's native JSON mode + Pydantic validation with retry, not regex:
```python
# Enforce structured output at the API level
from groq import Groq
client = Groq()

response = client.chat.completions.create(
    model=HACKER_MODEL,
    messages=[...],
    response_format={"type": "json_object"},  # Forces valid JSON
    temperature=0.1
)

# Parse with Pydantic — raises ValidationError on bad schema, trigger retry
findings = [VulnerabilityFinding(**f) for f in json.loads(response.choices[0].message.content)]
```

Better yet, migrate to LangChain/LangGraph `with_structured_output()` which handles all of this automatically.

### Bug 2: Only First Confirmed Vulnerability is Fixed

**In orchestrator.py**:
```python
# Stops at first confirmed vulnerability
for finding in findings:
    result = run_exploiter_agent(finding)
    if result['exploit_succeeded']:
        break  # ← Everything after this is ignored
```

**Impact**: A commit that introduces an SQL injection AND a hardcoded secret → only SQL injection gets a PR. The hardcoded secret is silently dropped. No log, no notification, no tracking.

**Fix**: Track all confirmed vulnerabilities and either:
- (Simple) Open one PR per confirmed vulnerability
- (Better) Open one PR that fixes all confirmed vulnerabilities, with one commit per fix
- (Best) Store all confirmed findings in the DB and run the Engineer/Verifier loop on each

### Bug 3: GitHub OAuth Token in Plaintext DB

**models.py**:
```python
github_token = Column(String)  # Raw token, no encryption
```

A DB leak, a backup mishap, or a SQLite file accidentally committed exposes every user's GitHub token. With these tokens, an attacker can push code to all monitored repos.

**Fix**:
```python
# Use Fernet symmetric encryption
from cryptography.fernet import Fernet

FERNET_KEY = Fernet.generate_key()  # Store in env var, not in DB

def encrypt_token(token: str) -> str:
    return Fernet(FERNET_KEY).encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    return Fernet(FERNET_KEY).decrypt(encrypted.encode()).decode()
```

### Bug 4: Auth Stored in localStorage (XSS Vector)

**aegis-frontend/app/auth/callback/page.tsx**:
```javascript
localStorage.setItem('user_id', user.id);
localStorage.setItem('github_token', user.token);  // ← Accessible to any JS on the page
```

If your frontend ever loads a third-party script that gets compromised (CDN attack, npm supply chain), that script can read the GitHub token from localStorage. This is a standard XSS attack vector.

**Fix**: Use `httpOnly` cookies set by the backend. They cannot be read by JavaScript at all:
```python
# FastAPI backend
response.set_cookie(
    key="session_token",
    value=signed_jwt,
    httponly=True,       # Not readable by JS
    secure=True,         # HTTPS only
    samesite="lax",      # CSRF protection
    max_age=86400
)
```

### Bug 5: Docker Subprocess Fallback in Production

**docker_runner.py**:
```python
try:
    # Run exploit in Docker
    container = client.containers.run(...)
except DockerException:
    # Fallback: run directly as subprocess
    result = subprocess.run(exploit_script, shell=True)  # ← DANGEROUS
```

If Docker daemon is not available (restart, crash, misconfiguration), the exploit code runs on the host machine with full network access and no memory limits. In production, a crafted exploit could escape to the host.

**Fix**: Hard fail if Docker is unavailable. Never fall back to subprocess for security-critical code:
```python
if not _docker_available():
    raise SandboxUnavailableError(
        "Docker daemon is not running. Cannot execute exploit code safely. "
        "Scan aborted for security reasons."
    )
```

---

## 3. Agent Architecture — Full Redesign Recommendations

### 3.1 Adopt LangGraph for Orchestration

The current `orchestrator.py` is a 500+ line imperative pipeline with manual state threading, manual retry logic, and manual error propagation. This is exactly what LangGraph was built to replace.

**Benefits of migrating**:
- **Persistent state**: If the server restarts mid-scan, the pipeline resumes from the last checkpoint — not from scratch
- **Built-in retry logic**: Conditional edges replace manual `for retry in range(MAX_RETRIES)` loops
- **Streaming**: LangGraph streams intermediate state, making SSE updates trivial
- **Debuggability**: LangSmith traces every agent call, every state transition
- **Human-in-the-loop**: Built-in `interrupt_before` for CRITICAL vulnerabilities

```python
# Conceptual LangGraph pipeline for Aegis
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

class AegisPipelineState(TypedDict):
    # Input
    repo_id: int
    commit_sha: str
    diff: str
    
    # Pre-processing
    semgrep_findings: list[dict]
    rag_context: str
    
    # Agent 1 output
    vulnerability_findings: list[VulnerabilityFinding]
    
    # Agent 2 output  
    confirmed_vulnerabilities: list[ConfirmedVuln]  # ALL confirmed, not just first
    exploit_scripts: dict[str, str]  # vuln_id → script
    
    # Agent 3 output (per vulnerability)
    patches: dict[str, PatchResult]  # vuln_id → {patched_code, test_code}
    
    # Agent 4 output
    verification_results: dict[str, VerificationResult]
    reviewer_diagnoses: list[ReviewerDiagnosis]  # Intelligent failure analysis
    
    # Control
    retry_count: int
    current_vulnerability_id: str
    pipeline_status: str
    error: Optional[str]

# Build the graph
graph = StateGraph(AegisPipelineState)
graph.add_node("pre_process", pre_process_node)
graph.add_node("finder", finder_node)
graph.add_node("exploiter", exploiter_node)
graph.add_node("engineer", engineer_node)
graph.add_node("verifier", verifier_node)  # Now a real LLM agent
graph.add_node("pr_creator", pr_creator_node)

# Conditional edges replace manual if/else
graph.add_conditional_edges("finder", route_after_finder, {
    "no_findings": END,
    "has_findings": "exploiter"
})

graph.add_conditional_edges("verifier", route_after_verification, {
    "success": "pr_creator",
    "retry": "engineer",        # Goes back with reviewer diagnosis
    "max_retries": END,
    "critical_needs_approval": "__interrupt__"  # Human in the loop
})

# Checkpointing - pipeline survives server restart
memory = SqliteSaver.from_conn_string("aegis.db")
app = graph.compile(checkpointer=memory)
```

### 3.2 Agent Model Strategy Improvements

| Agent | Current Model | Issue | Recommended |
|---|---|---|---|
| Finder | llama-3.3-70b (Groq) | Good speed, acceptable quality | ✅ Keep, add `response_format=json_object` |
| Exploiter | llama-3.3-70b (Groq) | Exploit code quality can be inconsistent | Consider `qwen-2.5-coder-32b` on Groq — stronger at code generation |
| Engineer | devstral-small-2505 (Mistral) | Good choice for patches | Add streaming + longer context window usage |
| Verifier | NONE (Python logic) | Missing the entire intelligence layer | Add `claude-sonnet-4-6` via Anthropic — best-in-class for reasoning about code failures |

**Why Claude for Verifier?**: The Reviewer needs to look at a pytest traceback + exploit output + patched code and reason about *why* the fix failed. This is a nuanced reasoning task, not code generation. Claude excels at structured reasoning over complex context.

### 3.3 Add a Context Agent (Agent 0)

Before the Finder runs, add a lightweight **Triage Agent** that:
1. Reads the commit message and PR description
2. Identifies which security domains are relevant (auth? SQL? crypto? file I/O?)
3. Produces a focused analysis brief for the Finder
4. Decides scan priority: emergency (crypto keys committed), standard, low

This saves tokens and improves Finder accuracy by narrowing the search space.

### 3.4 Fix: Handle All Confirmed Vulnerabilities

```python
# Instead of stopping at first confirmed vuln, collect all:

async def run_exploiter_for_all(findings: list[VulnerabilityFinding], ...) -> list[ConfirmedVuln]:
    confirmed = []
    for finding in findings:
        result = await run_exploiter_agent(finding, ...)
        if result['exploit_succeeded']:
            confirmed.append(ConfirmedVuln(
                finding=finding,
                exploit_script=result['exploit_script'],
                exploit_output=result['exploit_output']
            ))
    return confirmed  # All confirmed, not just first

# Then Engineer fixes them all:
for vuln in confirmed_vulnerabilities:
    patch = await run_engineer_agent(vuln, ...)
    verified = await run_verifier_agent(patch, vuln, ...)
    if verified.success:
        await create_pr_for_vuln(vuln, patch)
```

---

## 4. System Architecture Gaps

### 4.1 Database — Missing Migrations (Alembic)

**Current state**: `database/db.py` calls `Base.metadata.create_all(engine)` on startup. Any schema change requires deleting `aegis.db` and losing all data.

**Fix**: Add Alembic migration management:
```bash
pip install alembic
alembic init migrations
# Every schema change becomes a versioned migration file
alembic revision --autogenerate -m "add_cvss_score_to_scans"
alembic upgrade head
```

All migrations are tracked in version control. Zero data loss on schema changes.

### 4.2 SSE Polling — Replace with Event-Driven Push

**Current state**: `routes/scans.py` polls the database every 1 second per connected client. With 20 users watching active scans = 1,200 DB queries/minute doing nothing.

**Fix**: Use Redis pub/sub or a simple in-process event bus:
```python
# Instead of polling the DB, the orchestrator publishes events:
from asyncio import Queue

# Global event bus (or Redis channel in production)
scan_event_bus: dict[int, Queue] = {}  # scan_id → event queue

# Orchestrator publishes:
async def update_scan_status(scan_id, status, extra=None):
    await db_write(scan_id, status, extra)
    if scan_id in scan_event_bus:
        await scan_event_bus[scan_id].put({
            "status": status,
            "agent": extra.get("current_agent"),
            **extra
        })

# SSE endpoint subscribes:
@router.get("/stream/{scan_id}")
async def scan_stream(scan_id: int):
    queue = Queue()
    scan_event_bus[scan_id] = queue
    
    async def generate():
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            yield f"data: {json.dumps(event)}\n\n"
            if event['status'] in TERMINAL_STATES:
                break
    
    return EventSourceResponse(generate())
```

For production: use Redis pub/sub so multiple backend instances all push to the same channel.

### 4.3 No API Versioning or Rate Limiting

Every endpoint is `/api/scans`, not `/api/v1/scans`. When you change a response schema, every client breaks simultaneously with no migration path.

```python
# Add versioning prefix
app.include_router(scans_router, prefix="/api/v1/scans")
app.include_router(scans_router_v2, prefix="/api/v2/scans")  # Future

# Add rate limiting (slowapi)
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/trigger")
@limiter.limit("5/minute")  # 5 manual scan triggers per minute per IP
async def trigger_scan(request: Request, ...):
    ...
```

### 4.4 Missing: CVSS Scoring

Severity is a string from the LLM: `"CRITICAL"`, `"HIGH"`, etc. This is non-standardized and inconsistent between scans. The industry standard is CVSS v3.1.

Add a CVSS scoring step after the Finder:
```python
class CVSSScore(BaseModel):
    attack_vector: str          # NETWORK | ADJACENT | LOCAL | PHYSICAL
    attack_complexity: str      # LOW | HIGH
    privileges_required: str    # NONE | LOW | HIGH
    user_interaction: str       # NONE | REQUIRED
    scope: str                  # UNCHANGED | CHANGED
    confidentiality: str        # NONE | LOW | HIGH
    integrity: str              # NONE | LOW | HIGH
    availability: str           # NONE | LOW | HIGH
    base_score: float           # 0.0 – 10.0 (calculated)
    vector_string: str          # "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
```

The Finder agent can output these fields, and you calculate the base score programmatically (no LLM needed for the math).

### 4.5 Missing: Webhook Security for PR Events

Currently webhooks accept push events and PR events. But `pr_creator.py` opens PRs on behalf of Aegis. If someone opens a PR to a monitored repo from a fork, Aegis should NOT automatically run the pipeline on fork code — that's a code injection vector. Add explicit branch filtering:

```python
def should_process_event(payload: dict) -> bool:
    # Never process PRs from forks (could contain malicious code targeting Aegis itself)
    if payload.get('pull_request'):
        if payload['pull_request']['head']['repo']['fork']:
            logger.warning("Skipping fork PR - security policy")
            return False
    
    # Only process pushes to protected branches
    branch = payload.get('ref', '').replace('refs/heads/', '')
    if branch not in MONITORED_BRANCHES:
        return False
    
    return True
```

### 4.6 Missing: Idempotency / Duplicate Scan Prevention

If GitHub sends the same webhook twice (which it does, especially on retries), two identical scans start simultaneously. Both write to the same repo, potentially creating duplicate PRs.

```python
@router.post("/webhook/github")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await verify_and_parse(request)
    commit_sha = payload['after']
    repo_name = payload['repository']['full_name']
    
    # Check for duplicate
    with db_session() as session:
        existing = session.query(Scan).filter_by(
            commit_sha=commit_sha,
            repo_id=repo.id
        ).first()
        if existing:
            return {"status": "duplicate", "scan_id": existing.id}
    
    # Proceed with new scan
    background_tasks.add_task(run_aegis_pipeline, ...)
```

---

## 5. RAG System — Significant Improvements Available

### 5.1 Replace DefaultEmbeddingFunction with a Code-Specific Model

ChromaDB's `DefaultEmbeddingFunction` uses `all-MiniLM-L6-v2`, which was trained on natural language text, not code. For a security tool indexing Python, JavaScript, TypeScript, etc., this is meaningfully weaker than code-specific models.

**Recommended**: `jinaai/jina-embeddings-v2-base-code` or `microsoft/graphcodebert-base`

```python
from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction

# Purpose-built for code similarity
code_embedding_fn = HuggingFaceEmbeddingFunction(
    api_key=HUGGINGFACE_API_KEY,
    model_name="jinaai/jina-embeddings-v2-base-code"
)

collection = chroma_client.create_collection(
    name=repo_name,
    embedding_function=code_embedding_fn,
    metadata={"hnsw:space": "cosine"}
)
```

### 5.2 Index Security-Relevant Metadata More Deeply

Current indexer extracts function names and class names. Add:
- **Taint analysis markers**: which functions accept user input (`request.args`, `request.body`, `sys.argv`)
- **Sink markers**: which functions execute commands (`os.system`, `cursor.execute`, `eval`)
- **Auth boundaries**: functions decorated with `@login_required`, `@requires_auth`
- **Data flow annotations**: track input → sink paths at index time

This turns RAG from "find similar code" to "find the data flow path for this vulnerability."

### 5.3 Add Incremental Indexing

Currently the entire repo is re-indexed after each fix. For a repo with 200 files, fixing one file re-indexes all 200.

```python
def update_rag_incrementally(repo_path: str, changed_files: list[str]):
    """Only re-index files that changed, not the entire repo."""
    collection = get_collection(repo_path)
    for file_path in changed_files:
        doc_id = f"{repo_path}:{file_path}"
        collection.delete(ids=[doc_id])  # Remove old version
        new_doc = index_single_file(file_path)
        collection.upsert(**new_doc)     # Add new version
```

### 5.4 Add Vulnerability Pattern Library to RAG

Pre-seed the vector DB with known vulnerability patterns (OWASP, CWE top 25). When the Finder queries for context, it retrieves both repo-specific code AND known vulnerability patterns, dramatically improving pattern recognition for novel code.

---

## 6. Frontend / UX — Complete Overhaul Required

### 6.1 Critical Security Fix: Remove GitHub Data from localStorage

As described in Bug 4 above, auth state must move to httpOnly cookies. The frontend should never store tokens.

### 6.2 Missing: Error Boundaries

A single component error (e.g., malformed `findings_json` from DB) crashes the entire page with a blank screen. React error boundaries isolate failures:

```tsx
// components/ErrorBoundary.tsx
class ScanDetailBoundary extends React.Component {
  state = { hasError: false, error: null }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 border border-red-500/30 rounded-lg bg-red-950/20">
          <Shield className="text-red-400 mb-2" />
          <p className="text-red-300">Failed to load scan details.</p>
          <p className="text-xs text-zinc-500">{this.state.error?.message}</p>
          <Button onClick={() => this.setState({ hasError: false })}>Retry</Button>
        </div>
      )
    }
    return this.props.children
  }
}
```

### 6.3 Missing: Real-Time Pipeline Visualization (Major UX Gap)

The current UI shows which agent is "currently active" via `AgentAvatar`. This is far too minimal. Users pushed code and don't know what's happening for 45 seconds. The UI should feel like a live mission control panel:

**Recommended: Animated Pipeline Timeline Component**

```tsx
// Each agent card shows:
// - State: waiting | running | success | failed | skipped
// - Live log stream (last 3 log lines from that agent)  
// - Time elapsed for that specific phase
// - For Exploiter: show the exploit script being written in real time (streaming)
// - For Engineer: show the patch diff appearing character by character
// - For Verifier: show the test pass/fail indicators updating live

interface AgentPhaseCard {
  agent: 'finder' | 'exploiter' | 'engineer' | 'verifier'
  state: 'waiting' | 'running' | 'success' | 'failed'
  startTime?: Date
  elapsedMs?: number
  liveOutput?: string      // Streaming output
  finding?: VulnerabilityFinding
  result?: string
}
```

### 6.4 Missing: Vulnerability Detail Page

Currently there's a scan detail page but no vulnerability detail page. A single scan can have multiple findings (Finder returns a ranked list). Users need to drill into each finding independently.

**Add `/vulnerabilities/[id]` page** with:
- CVSS score breakdown (visual gauge)
- The vulnerable code block with syntax highlighting and line markers
- The exploit script (syntax-highlighted, read-only terminal)
- Live exploit execution replay
- The patch diff (before/after, unified view)
- Test results with pass/fail indicators per test
- "History" — has this vulnerability type appeared in this repo before?

### 6.5 Missing: Dashboard Intelligence Panel

The current dashboard stats are: total repos, active scans, vulnerabilities fixed, false positives. This is minimal.

**Add a proper intelligence dashboard**:
- **Vulnerability trend chart** (last 30 days, by severity) — use Recharts
- **Top vulnerability types** (pie/donut chart)
- **Time-to-fix distribution** (how long does your pipeline take on average?)
- **False positive rate** (are your scans noisy or precise?)
- **MTTR** (Mean Time to Remediate)
- **Risk score by repo** (horizontal bar chart)
- **Recent activity feed** (timeline of all scans with inline status chips)

### 6.6 Missing: Notification System

Currently users must have the dashboard open to know a scan completed. Add:

```tsx
// Browser push notifications (permission-based)
const notifyUser = (scan: Scan) => {
  if (Notification.permission === 'granted') {
    new Notification(`Aegis: ${scan.status}`, {
      body: scan.status === 'fixed' 
        ? `Fixed ${scan.vulnerability_type} in ${scan.repo_name} — PR opened`
        : `Scan failed: ${scan.error_message}`,
      icon: '/shield-icon.png',
      tag: `scan-${scan.id}`,  // Deduplicates notifications
    })
  }
}
```

Also: webhook/Slack notifications for CI/CD integration.

### 6.7 Missing: Human-in-the-Loop UI for CRITICAL Findings

CRITICAL severity vulnerabilities should never be auto-merged. Add an approval gate:

```tsx
// When a CRITICAL vuln is confirmed:
// 1. Pipeline pauses (LangGraph interrupt_before pr_creator)
// 2. Dashboard shows a prominent approval banner
// 3. User reviews: exploit proof, proposed patch, test results
// 4. User clicks "Approve PR" or "Reject & Review Manually"
// 5. Pipeline resumes or terminates

<CriticalApprovalBanner
  scan={scan}
  onApprove={() => api.approveCriticalFix(scan.id)}
  onReject={() => api.rejectFix(scan.id, reason)}
/>
```

### 6.8 Missing: Code Diff Viewer is Inadequate

Current `CodeDiff.tsx` is a basic before/after view. Replace with a proper diff renderer:

- Use `react-diff-viewer-continued` or `monaco-editor` for syntax highlighting
- Show line-level additions (green) and removals (red)
- Show the vulnerability location marker (yellow highlight) in the "before" panel
- Allow expanding/collapsing unchanged context lines

### 6.9 Add Search & Filter to Scan History

```tsx
// Scan history table should support:
<ScanHistoryTable
  filters={{
    status: ['fixed', 'failed', 'false_positive', 'clean'],
    severity: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
    vulnType: string,      // Free text search
    dateRange: [Date, Date],
    branch: string
  }}
  sortBy="created_at | severity | status"
  pagination={{ page: 1, perPage: 20 }}
/>
```

### 6.10 UX: Show Exploit Code with Warning Gate

The exploit terminal currently shows raw output. The *exploit script itself* should be viewable (for transparency) but behind a "Show exploit code" toggle with a clear warning:

```tsx
<ExploitCodeViewer
  script={scan.exploit_script}
  warning="This is the actual exploit code Aegis generated and ran to prove this vulnerability. It is shown for transparency only."
  collapsedByDefault={true}
  syntaxHighlight="python"
/>
```

---

## 7. Missing Features That Would Significantly Level Up the Product

### 7.1 Multi-Repository Batch Analysis

When a new vulnerability type is discovered in Repo A, Aegis should automatically scan all other monitored repos for the same pattern. This is the "Zero Day Response" use case — one exploit discovered → all repos checked in parallel.

### 7.2 PR Review Mode (Not Just Push Mode)

Currently Aegis only triggers on push. But the most impactful moment is *before* code merges. Add a PR review mode:
- Trigger on `pull_request.opened` and `pull_request.synchronize`
- Add inline review comments directly to the PR (via GitHub Review API)
- Block the PR merge if a CRITICAL vulnerability is confirmed

### 7.3 Security Regression Detection

If a PR reverts a previously-patched file, Aegis should detect the security regression:
```python
def check_for_regressions(diff: str, repo_id: int) -> list[SecurityRegression]:
    """
    Check if any changed files previously had vulnerabilities fixed by Aegis.
    If the patched code has been reverted or modified, flag it.
    """
    previous_fixes = db.query(Scan).filter_by(
        repo_id=repo_id, 
        status='fixed'
    ).all()
    
    for fix in previous_fixes:
        if fix.vulnerable_file in changed_files:
            # Check if the patch is still present
            if not patch_still_applied(fix, current_code):
                yield SecurityRegression(fix)
```

### 7.4 Vulnerability Knowledge Graph

Instead of storing findings as flat JSON, build a graph of vulnerability relationships:
- This CVE pattern appeared in commits X, Y, Z
- Repos A, B, C all had SQL injection in their ORM layer
- Developer @alice introduced 3 of the last 5 SQL injections (not for blame, for training)

Use Neo4j or simply a well-structured PostgreSQL schema with join tables.

### 7.5 Audit Log

Every action Aegis takes should be immutably logged:
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=utcnow)
    actor = Column(String)          # "aegis-pipeline" | "user:alice" | "scheduler"
    action = Column(String)         # "scan.started" | "pr.created" | "patch.applied"
    resource_type = Column(String)  # "scan" | "repo" | "vulnerability"
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String)
```

### 7.6 Export & Reporting

- **PDF security report** per repo (monthly summary, all vulnerabilities, fix rate)
- **SARIF export** (industry standard for security findings — works with GitHub Security tab)
- **CSV export** of scan history for compliance/audit

SARIF integration is the highest-value of these: it makes Aegis findings appear natively in GitHub's Security Advisories tab alongside other tools.

```python
def export_as_sarif(scans: list[Scan]) -> dict:
    """Export findings in SARIF 2.1.0 format for GitHub Security tab integration."""
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Aegis",
                    "version": "1.0.0",
                    "rules": [...]
                }
            },
            "results": [sarif_result(scan) for scan in scans]
        }]
    }
```

### 7.7 Scheduled Dependency Scanning

Beyond code analysis, add OSV (Open Source Vulnerability) database scanning for dependencies:
- Parse `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`
- Cross-reference against the OSV database (free, no API key required)
- Flag vulnerable dependencies with fix versions
- This runs separately from the exploit pipeline (no sandbox needed)

---

## 8. Observability & Production Readiness

### 8.1 Replace placeholder observability_stack.py

The current monitoring module is empty infrastructure. Add real observability:

```python
# Structured logging with correlation IDs
import structlog

log = structlog.get_logger()

async def run_aegis_pipeline(push_info: dict, scan_id: int):
    log = structlog.get_logger().bind(
        scan_id=scan_id,
        repo=push_info['repo_name'],
        commit=push_info['commit_sha'][:8]
    )
    
    log.info("pipeline.started")
    
    try:
        findings = await run_finder_agent(...)
        log.info("finder.completed", finding_count=len(findings), 
                 critical_count=sum(1 for f in findings if f.severity == 'CRITICAL'))
        ...
    except Exception as e:
        log.error("pipeline.failed", error=str(e), phase="finder")
        raise
```

### 8.2 Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics that matter for a security tool:
scans_total = Counter('aegis_scans_total', 'Total scans', ['status', 'repo'])
scan_duration = Histogram('aegis_scan_duration_seconds', 'Scan duration', ['phase'])
vulnerabilities_found = Counter('aegis_vulnerabilities_found_total', 'Vulns found', ['severity', 'type'])
false_positive_rate = Gauge('aegis_false_positive_rate', 'Current false positive rate')
patch_attempts = Histogram('aegis_patch_attempts', 'Number of Engineer retries needed')
```

### 8.3 Add Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "docker": await check_docker(),
            "groq_api": await check_groq(),
            "mistral_api": await check_mistral(),
            "chromadb": await check_chromadb(),
            "github_api": await check_github(),
        }
    }

@app.get("/ready")  # Kubernetes readiness probe
async def readiness():
    if not docker_available():
        raise HTTPException(503, "Docker not available — cannot safely execute exploits")
    return {"ready": True}
```

### 8.4 Add Proper Pagination to All List Endpoints

```python
@router.get("/api/v1/scans")
async def list_scans(
    repo_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
):
    offset = (page - 1) * per_page
    query = db.query(Scan).filter_by(repo_id=repo_id)
    
    if status:
        query = query.filter(Scan.status == status)
    if severity:
        query = query.filter(Scan.severity == severity)
    
    total = query.count()
    scans = query.order_by(Scan.created_at.desc()).offset(offset).limit(per_page).all()
    
    return {
        "data": scans,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page)
        }
    }
```

---

## 9. Technology Stack Recommendations

### Immediate Wins (Low Effort, High Impact)

| Change | Current | Recommended | Why |
|---|---|---|---|
| JSON structured output | regex fallback | `response_format=json_object` + Pydantic | Eliminates #1 reliability failure mode |
| Token encryption | plaintext | Fernet symmetric encryption | Eliminates credential leak risk |
| Auth cookie | localStorage | httpOnly cookie | Eliminates XSS attack surface |
| Docker hard fail | subprocess fallback | Hard exception on Docker unavailable | Eliminates sandbox escape risk |
| DB migrations | create_all() | Alembic | Zero data loss schema changes |
| Code embeddings | all-MiniLM-L6-v2 | jina-embeddings-v2-base-code | Meaningfully better code similarity |

### Medium-Term (Higher Effort, Game-Changing)

| Change | Benefit |
|---|---|
| Migrate orchestrator.py to LangGraph | Durable execution, human-in-the-loop, checkpoint/resume, streaming |
| Verifier → real LLM agent (Claude) | Intelligent failure diagnosis instead of raw error log passthrough |
| Redis for SSE events | Replace DB polling, scales to many concurrent users |
| SARIF export | Findings appear in GitHub Security tab natively |
| CVSS scoring | Standardized, comparable severity scores |
| PostgreSQL + connection pool | Production-grade database |


---

## 10. Implementation Roadmap

### Phase 1 — Security & Reliability (Week 1-2, Do Immediately)

**Non-negotiable fixes before any new features:**

- [ ] Remove Docker subprocess fallback — hard fail if Docker unavailable
- [ ] Encrypt GitHub tokens at rest (Fernet)
- [ ] Move auth from localStorage → httpOnly cookies
- [ ] Add `response_format=json_object` to all Groq API calls + Pydantic validation with retry
- [ ] Add Alembic migrations (never lose data again)
- [ ] Fix duplicate webhook handling (idempotency check on commit_sha)
- [ ] Add fork PR rejection in webhook handler

### Phase 2 — Agent Architecture (Week 2-4)

- [ ] Turn Verifier into a real LLM agent (Claude Sonnet) with `ReviewerDiagnosis` structured output
- [ ] Fix multi-vulnerability pipeline (collect all confirmed, fix all)
- [ ] Migrate orchestrator.py to LangGraph with checkpoint/resume
- [ ] Add CVSS scoring to Finder output
- [ ] Add Triage Agent (Agent 0) for commit context

### Phase 3 — Production Infrastructure (Week 4-6)

- [ ] Replace SSE DB polling with event bus (Redis pub/sub or asyncio Queue)
- [ ] Add API versioning (`/api/v1/`)
- [ ] Add rate limiting (slowapi)
- [ ] Add pagination to all list endpoints
- [ ] Replace SQLite with PostgreSQL
- [ ] Add structured logging with correlation IDs
- [ ] Add Prometheus metrics + `/health` + `/ready` endpoints

### Phase 4 — Frontend Overhaul (Week 6-8)

- [ ] Add React error boundaries to all pages
- [ ] Add real-time pipeline visualization (per-agent live output)
- [ ] Add proper code diff viewer (Monaco or react-diff-viewer)
- [ ] Add HITL approval UI for CRITICAL vulnerabilities
- [ ] Add browser push notifications
- [ ] Add search/filter to scan history
- [ ] Add intelligence dashboard (charts, MTTR, trends)
- [ ] Add exploit code viewer with warning gate

### Phase 5 — Feature Expansion (Week 8+)

- [ ] SARIF export (GitHub Security tab native integration)
- [ ] PR review mode (analyze before merge, add inline comments)
- [ ] Dependency vulnerability scanning (OSV database)
- [ ] Security regression detection
- [ ] PDF/CSV export
- [ ] Slack/webhook notifications
- [ ] Multi-repo batch scanning on new CVE discovery
- [ ] Vulnerability knowledge graph

---

## 11. Quick Reference — What to Fix First

If you only have time to fix five things, fix these, in this order:

1. **Remove subprocess fallback in docker_runner.py** — This can cause real damage if Docker goes down in production
2. **Encrypt GitHub tokens** — A DB leak currently exposes every user's GitHub access
3. **Move auth to httpOnly cookies** — localStorage auth tokens are an XSS liability
4. **Add `response_format=json_object` to all Groq calls** — The regex fallback is silently corrupting agent outputs
5. **Turn Verifier into a real LLM agent** — This is the core architectural requirement from the problem statement that is currently not implemented

Everything else is an improvement. These five are must-fixes.





## Recommended Architecture (Will go with this)

``
                  ┌──────────────────────────────────────────────┐
                  │            GATEWAY                        │
                  │   
                  └──────────────────────────────────────────────┘
                                      │
                              WEBHOOK RECEIVER
                           (FastAPI + GitHub App)
                                      │
                    ┌─────────────────▼──────────────────┐
                    │        LANGGRAPH SUPERVISOR          │
                    │   (Durable State + Retry Manager)    │
                    │   (Escalation + Cost Controller)     │
                    └───────────────┬─────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │(parallel)           │                 (parallel)
              ▼                     ▼                      ▼
    ┌──────────────┐     ┌──────────────────┐    ┌──────────────────┐
    │  AGENT D     │     │   AGENT A        │    │  AGENT E         │
    │ Taint Analyst│     │   The Hacker     │    │  CVE Scout       │
    │ (Haiku 4.5)  │     │ (Opus 4.7 +      │    │  (Haiku 4.5)     │
    │ CodeQL MCP   │     │  extended think) │    │  NVD/OSV MCP     │
    └──────┬───────┘     └──────┬───────────┘    └──────┬───────────┘
           │                    │                        │
           └──────────────┬─────┘                        │
                          │  Merged context              │
                          ▼                              ▼
                ┌──────────────────┐          ┌──────────────────┐
                │  Exploit Gen +   │          │  Dep CVE Report  │
                │  Confidence ≥0.7?│          │  EPSS Score High?│
                └────────┬─────────┘          └──────────────────┘
                     YES │                    (parallel PR comment)
                         ▼
                ┌──────────────────┐
                │   AGENT B        │
                │  The Engineer    │
                │ (Sonnet 4.6      │◄────────────────────┐
                │  + SKILL.md)     │                      │
                └────────┬─────────┘                      │
                         │ patch_diff                      │
                         ▼                                 │
                ┌──────────────────┐    REGRESSION/        │
                │   AGENT C        │    INCOMPLETE ────────┘
                │  The Reviewer    │    (with locked lines
                │ (GPT-4.1         │     + problem areas)
                │  SandboxAgent)   │
                └────────┬─────────┘
                         │ APPROVED
                         ▼
                ┌──────────────────┐
                │  Auto-merge PR   │
                │  + Memory        │
                │  Consolidation   │
                │  (Haiku 4.5)     │
                └──────────────────┘
```

---

## 📋 Phased Execution Plan

All tasks from this analysis have been broken down into actionable, step-by-step files in the `phases/` directory:

| File | Content |
|------|---------|
| [`PHASE_0_OVERVIEW.md`](phases/PHASE_0_OVERVIEW.md) | Master roadmap, dependency graph, technology decisions |
| [`PHASE_1_SECURITY.md`](phases/PHASE_1_SECURITY.md) | Remove subprocess fallback, encrypt tokens, httpOnly cookies, structured JSON |
| [`PHASE_2_AGENTS.md`](phases/PHASE_2_AGENTS.md) | Reviewer LLM agent, multi-vuln pipeline, standardized contracts |
| [`PHASE_3_LANGGRAPH.md`](phases/PHASE_3_LANGGRAPH.md) | State machine migration, Triage agent, CVSS scoring |
| [`PHASE_4_INFRASTRUCTURE.md`](phases/PHASE_4_INFRASTRUCTURE.md) | Event-driven SSE, Alembic, API versioning, rate limiting |
| [`PHASE_5_FRONTEND.md`](phases/PHASE_5_FRONTEND.md) | Error boundaries, pipeline viz, diff viewer, HITL approval |
| [`PHASE_6_INTELLIGENCE.md`](phases/PHASE_6_INTELLIGENCE.md) | Real threat engine, RAG overhaul, SARIF export |
| [`PHASE_7_FEATURES.md`](phases/PHASE_7_FEATURES.md) | PR review mode, dependency scanning, analytics |

**Execution order:** Phase 1 → Phases 2+4 (parallel) → Phase 3 → Phase 5 → Phase 6 → Phase 7 (ongoing)

---

## 12. Additional Findings (Independent Code Audit)

Issues discovered during line-by-line code audit — not covered in the original analysis above:


### Bug: `scheduler.py` calls `await run_aegis_pipeline(scan_info)` but pipeline is synchronous
- **File:** `scheduler.py:115`
- **Impact:** `run_aegis_pipeline()` is a synchronous function — `await` on it does nothing, but it blocks the async event loop for the entire pipeline duration (5+ minutes)
- **Fix:** Wrap in `asyncio.to_thread()` or `run_in_executor()`

### Bug: `update_scan_status()` creates a new DB session every call
- **File:** `orchestrator.py:33`
- **Impact:** Each status update opens and closes a new `SessionLocal()`. During a single pipeline run, this creates ~15 separate sessions — session leaks possible under load
- **Fix:** Pass the existing `db` session through the pipeline instead of creating new ones

### Bug: `get_scan()` returns tuple instead of raising HTTPException
- **File:** `routes/scans.py:152`
- **Impact:** `return {"error": "Scan not found"}, 404` returns a 200 with a tuple body — the 404 status code is never used
- **Fix:** `raise HTTPException(status_code=404, detail="Scan not found")`

### Bug: Fork PR detection missing
- **File:** `main.py:94-114`
- **Impact:** PRs from forks could contain malicious code that runs in the Aegis sandbox
- **Fix:** Check `payload["pull_request"]["head"]["repo"]["fork"]` — reject if True

### Bug: `clone_or_pull_repo()` doesn't check return codes
- **File:** `github_integration/diff_fetcher.py:16`
- **Impact:** `subprocess.run(["git", "pull"], ...)` can fail silently, leading to stale code analysis
- **Fix:** Add `check=True` or check `returncode`

### Design: `intelligence.py` imports modules that don't exist in some environments
- **File:** `routes/intelligence.py:16-18`
- **Impact:** Importing `scheduler_module.intelligent_scheduler`, `intelligence.threat_engine`, and `ml.vulnerability_predictor` — if any of these fail on import, the entire route module fails to load
- **Fix:** Lazy imports or graceful fallback

### Design: Demo mode has unreachable code path
- **File:** `sandbox/docker_runner.py:155-157`
- **Impact:** `config.DEMO_MODE` is checked after docker execution, but `_DEMO_MODE` at the top already returns before Docker runs — the `config.DEMO_MODE` check on line 155 is dead code
- **Fix:** Remove dead code on lines 155-157 and 274-275

### Bug: `_DEMO_EXPLOIT_CALL_COUNT` reset has no effect
- **File:** `orchestrator.py:157-161`
- **Impact:** The pipeline tries to reset a demo counter by importing `_DEMO_EXPLOIT_CALL_COUNT` and setting index `[0]` to `0`, but this variable doesn't exist in `docker_runner.py` — the import silently fails. The `try/except` swallows the `ImportError`. Demo mode's "first call succeeds, second fails" behavior is actually never enabled.
- **Fix:** Either remove entirely (demo mode already works via `_verifier_check` parameter) or implement correctly if needed

### Bug: `pr_creator.py` uses global `config.GITHUB_TOKEN` instead of per-user token
- **File:** `github_integration/pr_creator.py:20`
- **Impact:** `g = Github(config.GITHUB_TOKEN)` — PRs are always created with the backend's personal access token, not the user's OAuth token. This means: (a) PRs are attributed to the wrong account, (b) if `GITHUB_TOKEN` expires, ALL PR creation fails, (c) the user's `admin:repo_hook` scope may not match the backend token's permissions
- **Fix:** Pass `github_token` through the pipeline from the repo's user to `create_pull_request()`:
  ```python
  def create_pull_request(repo_full_name, ..., github_token=None):
      token = github_token or config.GITHUB_TOKEN
      g = Github(token)
  ```

### Bug: `notify_scan_update_sync()` is a no-op
- **File:** `routes/scans.py:20-27`
- **Impact:** The function body is just `pass` with a comment "SSE clients will poll the database." This is called from `orchestrator.py:117` inside `_broadcast()`, making the entire SSE notification path dead code. SSE only works because of the 1-second DB polling loop, which is the performance problem identified in section 4.2.
- **Fix:** Remove the dead function or implement the event bus (Phase 4 Task 4.1)

### Bug: Thread safety violation in orchestrator DB session
- **File:** `orchestrator.py:163-471`
- **Impact:** `run_aegis_pipeline()` creates a `SessionLocal()` at the top and uses it until `finally: db.close()`. But `update_scan_status()` (called throughout) creates its OWN separate `SessionLocal()`. Meanwhile, the pipeline runs in a background thread (`threading.Thread` from `routes/scans.py:211`). SQLite with `check_same_thread=False` only disables the Python thread check — concurrent writes from multiple threads can still corrupt data with "database is locked" errors.
- **Fix:** Use a single session per pipeline invocation and wrap writes in proper transactions

### Bug: `exploiter.py` doesn't handle empty diff
- **File:** `agents/exploiter.py` (user prompt construction)
- **Impact:** If `diff["changed_files"]` is empty but the pipeline reaches the exploiter (possible via synthetic diff fallback), the user prompt will contain empty code context, causing the LLM to generate generic/useless exploits
- **Fix:** Add early return if diff has no meaningful code content

### Design: `intelligent_scheduler.py` is 17KB but never tested
- **File:** `scheduler_module/intelligent_scheduler.py`
- **Impact:** This is the largest module in the project (17,846 bytes) but has zero test coverage and is only imported by `routes/intelligence.py`. If it has runtime errors, it would crash the intelligence API routes. The scheduler object is instantiated at import time.
- **Fix:** Add basic unit tests; consider lazy initialization

### Design: RAG retriever returns "No related context found." string on error
- **File:** `rag/retriever.py:43, 59-60`
- **Impact:** When ChromaDB is empty or throws an error, the retriever returns the literal string `"No related context found."` — the Finder agent then receives this text as RAG context and might include it in its reasoning. This is harmless but ugly.
- **Fix:** Return empty string `""` for clean context, and let the Finder prompt handle the absence of context explicitly

---

## 13. Architecture Code Smells

### 13.1 God Object: `orchestrator.py` (472 lines)

The orchestrator contains:
- DB session management (`SessionLocal`, `_get_repo_id`, `_create_scan`, `_update_scan`, `_complete_scan`)
- SSE broadcasting (`_broadcast`)
- Status update logic (`update_scan_status`)  
- Repository cloning logic
- Diff computation fallback
- Semgrep + RAG orchestration
- All four agent invocations
- PR creation
- Error handling for every phase

**This violates single-responsibility.** Each concern should be a separate module:
- `pipeline/pre_processor.py` — clone, diff, semgrep, RAG
- `pipeline/status_tracker.py` — DB status updates + SSE broadcasting
- `pipeline/graph.py` — LangGraph state machine (Phase 3)

### 13.2 Import Cycles

```
orchestrator.py → routes/scans.py (for notify_scan_update_sync)
routes/scans.py → orchestrator.py (for run_aegis_pipeline, in trigger endpoint)
```

This import-time circular dependency is currently hidden behind the `try/except` in `_broadcast()` (line 116: `from routes.scans import notify_scan_update_sync`). It works because the import is deferred. But any refactoring that moves imports to the top level will break with `ImportError`.

**Fix:** Extract the SSE event bus into a standalone `utils/event_bus.py` that both modules import. Neither should import the other.

### 13.3 Hardcoded Paths and Magic Strings

| Location | Magic Value | Should Be |
|----------|-------------|-----------|
| `docker_runner.py:48` | `'/app/'` | `config.CONTAINER_WORKDIR` |
| `docker_runner.py:132` | `"python"` entrypoint | `config.SANDBOX_PYTHON_BIN` |
| `pr_creator.py:26` | `f"aegis-fix-{...}-{random_id}"` | `config.PR_BRANCH_PREFIX` |
| `reviewer.py:67` | `"test_aegis_patch.py"` | `config.TEST_FILE_NAME` |
| `semgrep_runner.py:91` | `"p/security-audit"` | `config.SEMGREP_RULESET` |
| `repos.py:78` | `999999999` (dummy webhook ID) | Use `None` or a sentinel |

### 13.4 Error Swallowing

Multiple `try/except` blocks catch all exceptions and continue silently:

| File | Line | Exception Handling |
|------|------|--------------------|
| `orchestrator.py:139` | `except Exception: pass` | SSE broadcast failure silently dropped |
| `orchestrator.py:157-161` | `except Exception: pass` | Demo mode counter reset failure silently dropped |
| `reviewer.py:113-115` | `except Exception as e: logger.warning(...)` | RAG update failure only logged, not tracked |
| `rag/retriever.py:58-60` | `except Exception as e: return "No related..."` | ChromaDB error returns misleading string |

**Fix:** Track swallowed errors in a counter metric; at minimum log them with `logger.exception()` for stack traces.

---

## 14. Agent Prompt Engineering Gaps

### 14.1 Finder Agent — No Negative Instruction

The Finder prompt tells the LLM what to look for but never says what NOT to flag. This causes over-reporting:

```python
# MISSING from FINDER_SYSTEM_PROMPT:
"""
DO NOT flag the following as vulnerabilities:
- Type hints, docstrings, or comments mentioning security terms
- Test files containing intentionally vulnerable code
- Dependencies that handle their own input validation (e.g., SQLAlchemy ORM, parameterized queries)
- Dead code that is not reachable from any entry point
- Informational findings (e.g., "uses MD5" without context of how it's used)
"""
```

### 14.2 Exploiter Agent — No Failure Instrumentation

The Exploiter tells the LLM to write exploit code that outputs "VULNERABLE" or "NOT_VULNERABLE", but doesn't specify what to do on unexpected errors. Currently, if the exploit script itself crashes (e.g., syntax error, import missing), the sandbox sees `exit_code != 0` and treats it as "exploit failed = not vulnerable". This means a *buggy exploit* is classified as a *false positive*.

**Fix:** Add to Exploiter prompt:
```
If your exploit encounters an unexpected error (import error, syntax error, connection refused, etc.),
print "EXPLOIT_ERROR: <description>" and exit with code 2.
A crash is NOT the same as "not vulnerable" — it means the exploit needs debugging.
```

And in `docker_runner.py`:
```python
exploit_succeeded = exit_code == 0 and "VULNERABLE" in stdout and "NOT_VULNERABLE" not in stdout
exploit_errored = exit_code == 2 or "EXPLOIT_ERROR" in stdout  # NEW
# If exploit errored, don't mark as false positive — it needs retry
```

### 14.3 Engineer Agent — Missing Context Window Management

The Engineer receives: `vulnerable_code` + `file_path` + `exploit_output` + `vulnerability_type` + `error_logs`. But `vulnerable_code` could be a 1000-line file, and `error_logs` on retry contains the full pytest traceback (often 200+ lines).

With `ENGINEER_MAX_TOKENS=3000`, the response gets truncated mid-patch. The output is then garbage.

**Fix:**
- Truncate `vulnerable_code` to the relevant function ± 50 lines of context (use AST to find function boundaries)
- Truncate `error_logs` to the LAST failure only, not all retries
- Increase `ENGINEER_MAX_TOKENS` to 4000 for complex patches

### 14.4 No Temperature Control Across Agents

All agents use the Groq/Mistral API defaults for temperature (usually 1.0). For security analysis, this is too high — the Finder should have low temperature (0.1-0.2) for deterministic vulnerability detection, while the Exploiter could use slightly higher (0.3) for creative exploit strategies.

**Fix:**
```python
# config.py
FINDER_TEMPERATURE = float(os.getenv("FINDER_TEMPERATURE", "0.1"))
EXPLOITER_TEMPERATURE = float(os.getenv("EXPLOITER_TEMPERATURE", "0.3"))
ENGINEER_TEMPERATURE = float(os.getenv("ENGINEER_TEMPERATURE", "0.15"))
REVIEWER_TEMPERATURE = float(os.getenv("REVIEWER_TEMPERATURE", "0.1"))
```

---

## 15. Testing Strategy (Currently Missing)

The project has **zero test files**. No unit tests, no integration tests, no CI pipeline.

### 15.1 Unit Test Targets (Highest Value)

| Module | What to Test | Why |
|--------|-------------|-----|
| `agents/schemas.py` | Pydantic model validation for all agent I/O | Catches schema drift before production |
| `utils/crypto.py` | Encrypt → decrypt roundtrip, graceful fallback on invalid input | Token corruption = users locked out |
| `scanner/semgrep_runner.py` | `_parse_semgrep_output()` with sample JSON | Parsing changes silently break findings |
| `github_integration/webhook.py` | `verify_signature()` with valid/invalid signatures | Security-critical — must never pass forged webhooks |
| `github_integration/webhook.py` | `extract_push_info()` with sample payloads | Wrong field extraction = wrong files scanned |
| `sandbox/docker_runner.py` | Docker unavailable → hard fail (post Phase 1) | The most important safety test |

### 15.2 Integration Test Targets

| Test | What it Validates |
|------|-------------------|
| Full pipeline with demo mode | End-to-end: webhook → scan → exploit → patch → PR |
| SSE stream updates | Frontend receives status changes in order |
| Duplicate webhook rejection | Same commit SHA → no duplicate scan |
| OAuth flow → DB encryption | Login → token stored encrypted → decrypted on use |

### 15.3 Recommended Test Infrastructure

```bash
# Add to requirements.txt
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
httpx>=0.27  # For FastAPI TestClient

# Create test directory structure
tests/
├── conftest.py           # Fixtures: test DB, mock LLM client, mock Docker
├── test_schemas.py       # Pydantic model validation
├── test_crypto.py        # Token encryption roundtrip
├── test_webhook.py       # Signature verification
├── test_semgrep_parser.py # Semgrep JSON parsing
├── test_pipeline.py      # Integration: full pipeline with mocks
└── test_api.py           # API endpoint tests with TestClient
```

---

## 16. Current-State Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Security** | 3/10 | Plaintext tokens, subprocess fallback, localStorage auth, no fork protection |
| **Reliability** | 4/10 | Regex JSON fallback, no error boundaries, no duplicate prevention, thread safety issues |
| **Architecture** | 5/10 | Clean module separation, but God orchestrator, circular imports, no state machine |
| **Agent Quality** | 6/10 | Finder & Exploiter good, Engineer decent, Verifier missing (pure loop logic) |
| **Frontend** | 6/10 | Clean design system, real-time updates work, but no error handling, basic diff viewer |
| **RAG** | 4/10 | Functional but weak embeddings, whole-file chunking, no incremental indexing |
| **Intelligence** | 2/10 | Threat engine and ML predictor are placeholders returning hardcoded values |
| **Testing** | 0/10 | Zero test files. No CI. No coverage reporting. |
| **DevOps** | 3/10 | No Alembic, no health checks, no metrics, basic logging |
| **Documentation** | 5/10 | AGENTS.md exists, config is well-commented, but no API docs, no architecture diagram |

**Overall: 3.8/10** — Impressive prototype, but production deployment would be irresponsible without Phase 1 fixes.

**After Phase 1 + Phase 2: ~6.5/10** — Secure, reliable, intelligent agents. Ready for beta users.

**After all 7 phases: ~8.5/10** — Production-grade autonomous security platform.

---

## 17. Files Changed Since Last Analysis

*(Updated automatically — tracks what has been modified since the initial Update.md was written)*

| Date | File | Change |
|------|------|--------|
| 2026-04-24 | `agents/exploiter.py` | Migrated from Mistral SDK → Groq SDK |
| 2026-04-24 | `agents/engineer.py` | Fixed variable ordering bug for model assignment |
| 2026-04-24 | `config.py` | Fixed `GROQ_API_KEY` env var name mismatch |
| 2026-04-24 | `.env` | Updated model names for hybrid architecture |
| 2026-04-24 | `requirements.txt` | Added `groq` SDK dependency |
| 2026-04-24 | `.env.example` | Added `GROQ_API_KEY` template |
| 2026-04-25 | `phases/PHASE_0_OVERVIEW.md` | NEW — Master roadmap with dependency graph |
| 2026-04-25 | `phases/PHASE_1_SECURITY.md` | NEW — 7 security tasks with exact code changes |
| 2026-04-25 | `phases/PHASE_2_AGENTS.md` | NEW — 5 agent architecture tasks |
| 2026-04-25 | `phases/PHASE_3_LANGGRAPH.md` | NEW — 7 LangGraph migration tasks |
| 2026-04-25 | `phases/PHASE_4_INFRASTRUCTURE.md` | NEW — 7 backend hardening tasks |
| 2026-04-25 | `phases/PHASE_5_FRONTEND.md` | NEW — 7 frontend overhaul tasks |
| 2026-04-25 | `phases/PHASE_6_INTELLIGENCE.md` | NEW — 6 intelligence/RAG tasks |
| 2026-04-25 | `phases/PHASE_7_FEATURES.md` | NEW — 7 feature expansion tasks |
| 2026-04-25 | `Update.md` | Added Sections 12-17 (this update) |


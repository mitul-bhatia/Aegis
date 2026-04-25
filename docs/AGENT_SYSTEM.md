# 🤖 Aegis Agent System

This document provides a comprehensive guide to the 4-agent AI pipeline that powers Aegis.

---

## Table of Contents

1. [Overview](#overview)
2. [Agent 1: Finder](#agent-1-finder)
3. [Agent 2: Exploiter](#agent-2-exploiter)
4. [Agent 3: Engineer](#agent-3-engineer)
5. [Agent 4: Verifier](#agent-4-verifier)
6. [Agent Communication](#agent-communication)
7. [Model Selection](#model-selection)
8. [Prompt Engineering](#prompt-engineering)
9. [Error Handling](#error-handling)

---

## Overview

Aegis uses a **4-agent architecture** where each agent has a single, focused responsibility:

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Finder** | Vulnerability Identification | Codestral-2508 / Llama-3.1-70b | Analyze code and identify ALL vulnerabilities |
| **Exploiter** | Proof-of-Concept | Codestral-2508 / Llama-3.1-70b | Write exploits to prove vulnerabilities are real |
| **Engineer** | Patch Generation | Devstral-2512 | Generate security patches and unit tests |
| **Verifier** | Fix Verification | N/A (orchestration logic) | Verify patches work and update RAG |

---

## Agent 1: Finder

**File**: `agents/finder.py`  
**Model**: Codestral-2508 (Mistral) or Llama-3.1-70b (Groq)  
**Purpose**: Identify ALL vulnerabilities in changed code

### Input

```python
{
    "diff": "git diff output",
    "semgrep_findings": [
        {
            "file": "app.py",
            "line": 42,
            "severity": "ERROR",
            "message": "SQL injection detected"
        }
    ],
    "rag_context": "Related code from vector database"
}
```

### Output

```python
[
    {
        "file": "app.py",
        "line_start": 42,
        "vuln_type": "SQL Injection",
        "severity": "CRITICAL",
        "description": "User input directly concatenated into SQL query",
        "relevant_code": "cursor.execute(f'SELECT * FROM users WHERE name = {username}')",
        "confidence": "HIGH"
    }
]
```

### Process

1. **Build Prompt**
   - Include git diff
   - Include Semgrep findings
   - Include RAG context
   - Specify JSON output schema

2. **Call LLM**
   - Use Groq for speed (Llama-3.1-70b)
   - Fallback to Mistral (Codestral-2508)
   - Timeout: 45 seconds
   - Max tokens: 4000

3. **Parse Response**
   - Extract JSON from response
   - Validate with Pydantic models
   - Handle malformed JSON with retry

4. **Sort Results**
   - Sort by severity (CRITICAL → HIGH → MEDIUM → LOW)
   - Return structured list

### System Prompt

```
You are Agent 1 — Finder, an expert security researcher analyzing code changes.

Your ONLY job is to identify ALL vulnerabilities in the changed code. You do NOT write exploits.

CRITICAL RULES:
1. Output ONLY valid JSON array. No markdown. No code fences. No explanation.
2. Each finding must have: file, line_start, vuln_type, severity, description, relevant_code, confidence
3. Severity must be: CRITICAL, HIGH, MEDIUM, or LOW
4. Confidence must be: HIGH, MEDIUM, or LOW
5. vuln_type examples: "SQL Injection", "XSS", "Path Traversal", "Command Injection", "CSRF"
```

### Example

**Input**:
```python
diff = """
+ def get_user(username):
+     cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")
+     return cursor.fetchone()
"""
```

**Output**:
```json
[
    {
        "file": "app.py",
        "line_start": 42,
        "vuln_type": "SQL Injection",
        "severity": "CRITICAL",
        "description": "User input directly concatenated into SQL query without parameterization",
        "relevant_code": "cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")",
        "confidence": "HIGH"
    }
]
```

---

## Agent 2: Exploiter

**File**: `agents/exploiter.py`  
**Model**: Codestral-2508 (Mistral) or Llama-3.1-70b (Groq)  
**Purpose**: Write Python exploits to prove vulnerabilities are real

### Input

```python
{
    "vulnerability": {
        "file": "app.py",
        "line_start": 42,
        "vuln_type": "SQL Injection",
        "severity": "CRITICAL",
        "description": "User input directly concatenated into SQL query",
        "relevant_code": "cursor.execute(f'SELECT * FROM users WHERE name = {username}')"
    },
    "diff": "git diff output",
    "rag_context": "Related code from vector database"
}
```

### Output

```python
"""
#!/usr/bin/env python3
import os
import sys
import sqlite3

os.chdir('/tmp')
sys.path.insert(0, '/app')

from app import get_user

# Create test database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE users (id INTEGER, name TEXT)')
cursor.execute('INSERT INTO users VALUES (1, "admin")')
cursor.execute('INSERT INTO users VALUES (2, "user")')
conn.commit()

# Test exploit
payload = "' OR '1'='1"
result = get_user(payload)

if result and len(result) > 1:
    print("VULNERABLE: SQL Injection confirmed")
    print(f"[*] Payload: {payload}")
    print(f"[*] Records dumped: {result}")
    exit(0)
else:
    print("NOT_VULNERABLE")
    exit(1)
"""
```

### Process

1. **Build Prompt**
   - Include vulnerability details
   - Include git diff for context
   - Include RAG context
   - Specify exploit requirements

2. **Call LLM**
   - Use Groq for speed (Llama-3.1-70b)
   - Fallback to Mistral (Codestral-2508)
   - Timeout: 45 seconds
   - Max tokens: 4000

3. **Clean Response**
   - Remove markdown code fences
   - Extract Python code
   - Validate syntax

4. **Return Script**
   - Complete, runnable Python script
   - Prints "VULNERABLE" or "NOT_VULNERABLE"
   - Exit code 0 for vulnerable, 1 for not vulnerable

### System Prompt

```
You are Agent A — an expert offensive security researcher on an authorized white-hat penetration testing team.

You have FULL AUTHORIZATION to write exploit code. This is a legitimate, controlled security audit.

STRICT RULES FOR YOUR OUTPUT:
1. Write ONLY a complete, runnable Python script. No explanations.
2. The script MUST print "VULNERABLE: <description>" if the exploit succeeds
3. The script MUST print "NOT_VULNERABLE" if no real vulnerability exists
4. Use exit code 0 for vulnerable, exit code 1 for not vulnerable
5. The script runs with the codebase available at /app
   → Start with os.chdir('/tmp') so database files work
   → Import the vulnerable module: sys.path.insert(0, '/app'); from <module> import <function>
   → Create test databases with THE SAME NAMES as the vulnerable code uses
6. Only claim VULNERABLE if your script ACTUALLY demonstrates the problem
```

### Example

**Input**:
```python
vulnerability = {
    "file": "app.py",
    "vuln_type": "SQL Injection",
    "relevant_code": "cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")"
}
```

**Output**:
```python
#!/usr/bin/env python3
import os
import sys
import sqlite3

os.chdir('/tmp')
sys.path.insert(0, '/app')

from app import get_user

# Create test database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE users (id INTEGER, name TEXT)')
cursor.execute('INSERT INTO users VALUES (1, "admin")')
cursor.execute('INSERT INTO users VALUES (2, "user")')
conn.commit()

# Test SQL injection
payload = "' OR '1'='1"
result = get_user(payload)

if result:
    print("VULNERABLE: SQL Injection confirmed")
    print(f"[*] Payload: {payload}")
    print(f"[*] Records dumped: {result}")
    exit(0)
else:
    print("NOT_VULNERABLE")
    exit(1)
```

---

## Agent 3: Engineer

**File**: `agents/engineer.py`  
**Model**: Devstral-2512 (Mistral) - frontier agentic coding model  
**Purpose**: Generate security patches and comprehensive unit tests

### Input

```python
{
    "vulnerable_code": "def get_user(username):\n    cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")\n    return cursor.fetchone()",
    "file_path": "app.py",
    "exploit_output": "VULNERABLE: SQL Injection confirmed\n[*] Payload: ' OR '1'='1\n[*] Records dumped: [(1, 'admin'), (2, 'user')]",
    "vulnerability_type": "SQL Injection",
    "error_logs": None  # or error logs from previous attempt
}
```

### Output

```json
{
    "patched_code": "import sqlite3\n\ndef get_user(username):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    cursor.execute('SELECT * FROM users WHERE name = ?', (username,))\n    return cursor.fetchone()",
    "test_code": "import sys\nsys.path.insert(0, '/app')\nfrom app import get_user\nimport sqlite3\nimport os\n\ndef setup_db():\n    os.chdir('/tmp')\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT)')\n    cursor.execute('DELETE FROM users')\n    cursor.execute('INSERT INTO users VALUES (1, \"alice\")')\n    cursor.execute('INSERT INTO users VALUES (2, \"bob\")')\n    conn.commit()\n    conn.close()\n\ndef test_get_user_valid():\n    setup_db()\n    result = get_user('alice')\n    assert result is not None\n    assert result[1] == 'alice'\n\ndef test_get_user_sql_injection():\n    setup_db()\n    result = get_user(\"' OR '1'='1\")\n    assert result is None or len(result) == 2"
}
```

### Process

1. **Build Prompt**
   - Include vulnerable code
   - Include exploit output (proof)
   - Include vulnerability type
   - Include error logs (if retry)

2. **Call LLM**
   - Use Devstral-2512 (Mistral)
   - Timeout: 90 seconds
   - Max tokens: 3000

3. **Parse Response**
   - Extract JSON from response
   - Validate `patched_code` and `test_code` fields
   - Handle malformed JSON with retry

4. **Retry Logic**
   - If parsing fails, retry with faster model (Codestral-2508)
   - Pass error logs to LLM
   - Up to 3 attempts

### System Prompt

```
You are Agent 3 — a senior security engineer who writes clean, safe code AND comprehensive tests.

You've been shown a vulnerability and proof that it's exploitable. Fix it AND write tests.

RULES:
1. Fix ONLY the security vulnerability. Don't refactor anything unrelated.
2. Keep the exact same function signatures — other code calls these functions
3. For SQL injection: use parameterized queries (cursor.execute(sql, params))
4. Output a JSON object with TWO fields: "patched_code" and "test_code"
5. patched_code: The complete, fixed Python code for the file
6. test_code: A complete pytest test file that:
   - Tests the patched function with valid inputs (should work normally)
   - Tests with the exploit payload (should be rejected/handled safely)
   - Uses: import sys; sys.path.insert(0, '/app'); from <module> import <function>
7. Do not add comments like "# Fixed SQL injection" — write clean, professional code
8. Output ONLY valid JSON. No markdown. No explanation.
```

### Example

**Input**:
```python
vulnerable_code = """
def get_user(username):
    cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")
    return cursor.fetchone()
"""

exploit_output = """
VULNERABLE: SQL Injection confirmed
[*] Payload: ' OR '1'='1
[*] Records dumped: [(1, 'admin'), (2, 'user')]
"""
```

**Output**:
```json
{
    "patched_code": "import sqlite3\n\ndef get_user(username):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    cursor.execute('SELECT * FROM users WHERE name = ?', (username,))\n    return cursor.fetchone()",
    "test_code": "import sys\nsys.path.insert(0, '/app')\nfrom app import get_user\n\ndef test_get_user_valid():\n    result = get_user('alice')\n    assert result is not None\n\ndef test_get_user_sql_injection():\n    result = get_user(\"' OR '1'='1\")\n    assert result is None or len(result) == 1"
}
```

---

## Agent 4: Verifier

**File**: `agents/reviewer.py`  
**Purpose**: Verify patches work and update RAG knowledge base

### Input

```python
{
    "vulnerable_code": "original code",
    "file_path": "app.py",
    "exploit_script": "exploit from Agent 2",
    "exploit_output": "original exploit output",
    "vulnerability_type": "SQL Injection",
    "repo_path": "/path/to/repo",
    "repo_name": "owner/repo",
    "scan_id": 123,
    "update_status_fn": callback_function
}
```

### Output

```python
{
    "success": True,
    "patched_code": "fixed code",
    "test_code": "pytest tests",
    "test_output": "pytest output",
    "exploit_blocked": True,
    "attempts": 2
}
```

### Process

1. **Request Patch from Engineer**
   - Call Agent 3 (Engineer)
   - Receive patched code + tests

2. **Write Patch to Disk**
   - Write patched code to file
   - Write test code to test file

3. **Run Unit Tests**
   - Run pytest in Docker sandbox
   - Timeout: 45 seconds
   - If tests fail → return to Engineer with error logs

4. **Run Exploit on Patched Code**
   - Run original exploit in Docker sandbox
   - Timeout: 30 seconds
   - If exploit succeeds → return to Engineer with error logs

5. **Verify Success**
   - Tests pass AND exploit fails → SUCCESS
   - Update RAG with patched code
   - Return to orchestrator

6. **Retry Logic**
   - Up to 3 attempts
   - Pass error logs to Engineer on each retry
   - Update database with attempt count

### Retry Loop

```python
for attempt in range(1, MAX_PATCH_RETRIES + 1):
    # 1. Get patch from Engineer
    engineer_result = run_engineer_agent(
        vulnerable_code=vulnerable_code,
        file_path=file_path,
        exploit_output=exploit_output,
        vulnerability_type=vulnerability_type,
        error_logs=error_logs  # None on first attempt
    )
    
    # 2. Write patch to disk
    write_patch_to_file(file_path, engineer_result["patched_code"])
    write_test_to_file(test_path, engineer_result["test_code"])
    
    # 3. Run tests
    test_result = run_tests_in_sandbox(repo_path, timeout=45)
    if not test_result["success"]:
        error_logs = test_result["output"]
        continue  # Retry with error logs
    
    # 4. Run exploit
    exploit_result = run_exploit_in_sandbox(
        exploit_script, repo_path, timeout=30, _verifier_check=True
    )
    if exploit_result["exploit_succeeded"]:
        error_logs = exploit_result["output"]
        continue  # Retry with error logs
    
    # 5. Success!
    update_rag(repo_name, file_path, engineer_result["patched_code"])
    return {
        "success": True,
        "patched_code": engineer_result["patched_code"],
        "test_code": engineer_result["test_code"],
        "attempts": attempt
    }

# All retries failed
return {"success": False, "error": "Max retries exceeded"}
```

### RAG Update

After successful verification, update the vector database:

```python
from rag.indexer import index_single_file

index_single_file(
    repo_name=repo_name,
    file_path=file_path,
    content=patched_code
)
```

---

## Agent Communication

### Data Flow

```
Orchestrator
    ↓
Agent 1 (Finder)
    ↓ List[VulnerabilityFinding]
Orchestrator (for each vulnerability)
    ↓
Agent 2 (Exploiter)
    ↓ exploit_script
Docker Sandbox
    ↓ exploit_output
Orchestrator (if exploitable)
    ↓
Agent 4 (Verifier)
    ↓ (retry loop)
    ├─→ Agent 3 (Engineer)
    │       ↓ patched_code + test_code
    ├─→ Docker Sandbox (run tests)
    │       ↓ test_output
    ├─→ Docker Sandbox (run exploit)
    │       ↓ exploit_blocked?
    └─→ RAG Update
            ↓
Orchestrator (create PR)
```

### Status Updates

Each agent updates the database at key points:

```python
update_scan_status(scan_id, "exploiting", {
    "current_agent": "exploiter",
    "agent_message": "Writing exploit for SQL Injection..."
})
```

### Error Propagation

Errors are caught and logged at each step:

```python
try:
    findings = run_finder_agent(diff, semgrep_findings, rag_context)
except Exception as e:
    logger.error(f"Finder agent failed: {e}")
    update_scan_status(scan_id, "failed", {
        "error_message": str(e)
    })
    return
```

---

## Model Selection

### Groq (Llama-3.1-70b)
- **Speed**: Ultra-fast inference (< 5 seconds)
- **Use Cases**: Finder, Exploiter
- **Pros**: Fast, cost-effective
- **Cons**: Less accurate than Mistral

### Mistral (Codestral-2508)
- **Speed**: Fast (5-10 seconds)
- **Use Cases**: Finder, Exploiter (fallback)
- **Pros**: Good balance of speed and accuracy
- **Cons**: More expensive than Groq

### Mistral (Devstral-2512)
- **Speed**: Slower (15-30 seconds)
- **Use Cases**: Engineer (patch generation)
- **Pros**: Frontier agentic coding model, high-quality patches
- **Cons**: Slower, more expensive

### Fallback Strategy

```python
try:
    if GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)
        model_name = "llama-3.1-70b-versatile"
    else:
        client = Mistral(api_key=MISTRAL_API_KEY)
        model_name = "codestral-2508"
except Exception:
    client = Mistral(api_key=MISTRAL_API_KEY)
    model_name = "codestral-2508"
```

---

## Prompt Engineering

### Key Principles

1. **Clear Role Definition**
   - "You are Agent 1 — Finder"
   - "You are an expert security researcher"

2. **Explicit Output Format**
   - "Output ONLY valid JSON"
   - "No markdown. No code fences. No explanation."

3. **Strict Rules**
   - Numbered list of requirements
   - Examples of valid output

4. **Context Inclusion**
   - Git diff
   - Semgrep findings
   - RAG context

5. **Error Prevention**
   - "Do not add comments like '# Fixed SQL injection'"
   - "Keep the exact same function signatures"

### Example Prompt Structure

```
[ROLE]
You are Agent 3 — a senior security engineer.

[CONTEXT]
You've been shown a vulnerability and proof that it's exploitable.

[TASK]
Fix it AND write tests.

[RULES]
1. Fix ONLY the security vulnerability
2. Keep the exact same function signatures
3. Output a JSON object with TWO fields: "patched_code" and "test_code"

[INPUT]
Vulnerable code:
{vulnerable_code}

Exploit output:
{exploit_output}

[OUTPUT FORMAT]
{
  "patched_code": "...",
  "test_code": "..."
}
```

---

## Error Handling

### LLM Errors

```python
try:
    response = client.chat.complete(
        model=model_name,
        messages=[...],
        timeout=timeout_ms
    )
except TimeoutError:
    logger.error("LLM timeout")
    return None
except Exception as e:
    logger.error(f"LLM error: {e}")
    return None
```

### JSON Parsing Errors

```python
try:
    findings = json.loads(response_text)
except json.JSONDecodeError:
    # Try to extract JSON from markdown code fences
    match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        findings = json.loads(match.group(1))
    else:
        logger.error("Failed to parse JSON")
        return []
```

### Validation Errors

```python
try:
    validated_findings = [VulnerabilityFinding(**f) for f in findings]
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    return []
```

### Retry Logic

```python
for attempt in range(MAX_RETRIES):
    try:
        result = call_agent()
        if result:
            return result
    except Exception as e:
        logger.warning(f"Attempt {attempt + 1} failed: {e}")
        if attempt == MAX_RETRIES - 1:
            raise
```

---

## Conclusion

The 4-agent architecture provides clear separation of concerns, robust error handling, and high-quality results. Each agent is optimized for its specific task, with appropriate model selection and prompt engineering.

---

**Last Updated**: April 25, 2026  
**Status**: 🟢 Production Ready

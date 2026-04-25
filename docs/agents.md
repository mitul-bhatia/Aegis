# Aegis Agent System

## Overview

Aegis implements a **7-agent pipeline** using LangGraph for autonomous vulnerability remediation. Each agent is specialized for a specific task in the security workflow.

## Agent Architecture

### Pipeline Flow
```
pre_process → finder → exploiter → engineer → safety_validator → approval_gate → pr_creator
     ↓           ↓         ↓           ↓            ↓              ↓           ↓
   clean?     no vulns?  no exploits? patch failed? new issues?  critical?   more vulns?
     ↓           ↓         ↓           ↓            ↓              ↓           ↓
    END        END       END      retry/END    retry engineer    END      loop back
```

### State Management
All agents share a common `AegisPipelineState` (TypedDict) that flows through the pipeline:

```python
class AegisPipelineState(TypedDict):
    # Input data
    repo_full_name: str
    commit_sha: str
    branch: str
    scan_id: Optional[int]
    
    # Processing results
    local_repo_path: str
    diff: dict
    semgrep_findings: List[dict]
    rag_context: str
    
    # Agent outputs
    vulnerability_findings: List[dict]
    confirmed_vulnerabilities: List[dict]
    patched_code: Optional[str]
    test_code: Optional[str]
    
    # Control flow
    current_vuln_index: int
    verification_passed: bool
    pipeline_status: str
    awaiting_approval: bool
```

## Individual Agents

### 1. Pre-Process Node
**File**: `pipeline/nodes.py:pre_process_node()`

**Purpose**: Repository preparation and initial analysis

**Implementation**:
```python
def pre_process_node(state: AegisPipelineState) -> dict:
    # 1. Clone repository locally
    repo_path = clone_repository(repo_url, commit_sha)
    
    # 2. Generate git diff
    diff = get_git_diff(repo_path, commit_sha)
    
    # 3. Run Semgrep on changed files
    semgrep_findings = run_semgrep_on_files(changed_files, repo_path)
    
    # 4. Get RAG context from ChromaDB
    rag_context = get_related_code_context(changed_files)
    
    # 5. Scan for dependency vulnerabilities
    dependency_vulns = run_dependency_scan(repo_path)
```

**Exit Conditions**:
- No code files changed → `pipeline_status = "clean"` → END
- Continue to Finder if code changes detected

**Performance**: ~10-15 seconds including repository clone

### 2. Finder Agent
**File**: `agents/finder.py:run_finder_agent()`

**Purpose**: AI-powered vulnerability detection and classification

**Model Configuration**:
- **Provider**: GROQ (10-20x faster than Mistral)
- **Model**: `llama-3.3-70b-versatile`
- **Timeout**: 45 seconds
- **Max Tokens**: 4000

**Implementation**:
```python
def run_finder_agent(semgrep_findings, diff, rag_context):
    # 1. Build context prompt with Semgrep findings
    prompt = build_finder_prompt(semgrep_findings, diff, rag_context)
    
    # 2. Call GROQ API for analysis
    response = call_groq_api(prompt)
    
    # 3. Parse structured JSON response
    findings = parse_findings_json(response)
    
    # 4. Validate and enrich findings
    return validate_findings(findings)
```

**Output Structure**:
```python
class VulnerabilityFinding:
    vulnerability_type: str      # e.g., "SQL Injection"
    severity: str               # CRITICAL, HIGH, MEDIUM, LOW
    cwe_id: str                # e.g., "CWE-89"
    owasp_category: str        # e.g., "A03:2021 – Injection"
    file_path: str             # Vulnerable file
    line_number: int           # Exact line location
    vulnerable_code: str       # Code snippet
    explanation: str           # Detailed vulnerability description
    impact_assessment: str     # Potential impact analysis
```

**Exit Conditions**:
- No vulnerabilities found → END
- Vulnerabilities found → Continue to Exploiter

**Performance**: ~5-10 seconds with GROQ

### 3. Exploiter Agent
**File**: `agents/exploiter.py:run_exploiter_agent()`

**Purpose**: Generate and execute proof-of-concept exploits

**Model Configuration**:
- **Provider**: GROQ
- **Model**: `llama-3.3-70b-versatile`
- **Timeout**: 45 seconds

**Implementation**:
```python
def run_exploiter_agent(finding, diff, rag_context):
    # 1. Build exploit generation prompt
    prompt = build_exploit_prompt(finding, diff, rag_context)
    
    # 2. Generate Python exploit script
    exploit_script = call_groq_api(prompt)
    
    # 3. Execute in Docker sandbox
    result = run_exploit_in_sandbox(exploit_script, repo_path)
    
    # 4. Validate exploit success
    return validate_exploit_result(result)
```

**Docker Sandbox Execution**:
```python
def run_exploit_in_sandbox(exploit_script, repo_path):
    container = docker_client.containers.run(
        "aegis-sandbox:latest",
        volumes={
            tmpdir: {"bind": "/sandbox", "mode": "ro"},
            repo_path: {"bind": "/app", "mode": "ro"}
        },
        network_mode="none",           # No internet
        mem_limit="256m",              # Memory limit
        cpu_quota=50000,               # 50% CPU
        user="sandbox",                # Non-root
        cap_drop=["ALL"],              # No capabilities
        timeout=30                     # 30-second limit
    )
```

**Success Criteria**:
- Exit code = 0
- Output contains "VULNERABLE"
- Output does NOT contain "NOT_VULNERABLE"

**Exit Conditions**:
- No exploits succeed → `pipeline_status = "false_positive"` → END
- Docker unavailable → `pipeline_status = "failed"` → END
- Exploits confirmed → Continue to Engineer

**Performance**: ~30-60 seconds including sandbox execution

### 4. Engineer Agent
**File**: `agents/engineer.py:run_engineer_agent()`

**Purpose**: Generate secure patches and comprehensive tests

**Model Configuration**:
- **Provider**: Mistral (specialized for code generation)
- **Primary Model**: `devstral-small-2505`
- **Retry Model**: `devstral-2512` (larger for complex fixes)
- **Timeout**: 90 seconds
- **Max Tokens**: 3000

**Implementation**:
```python
def run_engineer_agent(vulnerability, original_code, rag_context):
    # 1. Build patch generation prompt
    prompt = build_engineer_prompt(vulnerability, original_code, rag_context)
    
    # 2. Generate patch with Mistral
    response = call_mistral_api(prompt, model="devstral-small-2505")
    
    # 3. Parse patch and test code
    patch_result = parse_engineer_output(response)
    
    # 4. Apply patch to file
    apply_patch(patch_result.patched_code, file_path)
    
    # 5. Run verification tests
    test_result = run_tests_in_sandbox(repo_path)
    
    # 6. Re-run exploit to confirm fix
    exploit_result = run_exploit_in_sandbox(original_exploit, repo_path)
    
    return validate_patch_success(test_result, exploit_result)
```

**Output Structure**:
```python
class EngineerOutput:
    patched_code: str          # Complete fixed file content
    test_code: str             # Comprehensive test suite
    explanation: str           # Patch explanation
    security_rationale: str    # Why this fix is secure
```

**Verification Process**:
1. **Test Execution**: Run generated tests in Docker sandbox
2. **Exploit Re-execution**: Confirm original exploit now fails
3. **Code Quality**: Validate patch doesn't break existing functionality

**Retry Logic**:
- Max 3 attempts per vulnerability
- Uses larger model (`devstral-2512`) for retries
- Increments `current_vuln_index` on final failure

**Exit Conditions**:
- Patch successful → Continue to Safety Validator
- Patch failed after retries → Next vulnerability or END

**Performance**: ~60-120 seconds including verification

### 5. Safety Validator
**File**: `pipeline/safety_validator.py:safety_validator_node()`

**Purpose**: Prevent regressions and detect new vulnerabilities

**Implementation**:
```python
def safety_validator_node(state):
    # 1. Re-run Semgrep on ALL diff files (not just patched file)
    all_diff_files = get_all_changed_files(diff)
    post_patch_findings = run_semgrep_on_files(all_diff_files, repo_path)
    
    # 2. Compare against pre-patch baseline
    pre_patch_findings = state["semgrep_findings"]
    new_findings = detect_new_findings(post_patch_findings, pre_patch_findings)
    
    # 3. Check for regressions against known signatures
    regressions = check_for_regressions(repo_id, post_patch_findings, scan_id)
    
    # 4. Evaluate safety
    if new_findings or regressions:
        if rescan_count < 1:
            return {"rescan_needed": True, "rescan_count": rescan_count + 1}
        else:
            # Accept with warning after 1 retry
            pass
    
    return {"rescan_needed": False}
```

**Safety Checks**:
1. **New Vulnerability Detection**: Compares post-patch vs pre-patch Semgrep results
2. **Regression Detection**: Checks against database of known vulnerability signatures
3. **Full Diff Analysis**: Scans all changed files, not just the patched one

**Retry Logic**:
- Max 1 retry if issues detected
- Loops back to Engineer for another attempt
- Accepts patch with warning if issues persist after retry

**Exit Conditions**:
- Safety checks pass → Continue to Approval Gate
- Issues detected → Loop back to Engineer (if retries available)

### 6. Approval Gate
**File**: `pipeline/nodes.py:approval_gate_node()`

**Purpose**: Human oversight for critical vulnerabilities

**Implementation**:
```python
def approval_gate_node(state):
    confirmed = state["confirmed_vulnerabilities"]
    idx = state["current_vuln_index"]
    
    if idx >= len(confirmed):
        return {}
    
    current_vuln = confirmed[idx]
    severity = current_vuln["finding"]["severity"]
    
    # CRITICAL vulnerabilities require human approval
    if severity == "CRITICAL":
        update_scan_status(scan_id, "awaiting_approval", {
            "message": "Critical vulnerability requires human review",
            "vulnerability": current_vuln["finding"]["vulnerability_type"]
        })
        return {"awaiting_approval": True}
    
    # Non-critical vulnerabilities proceed automatically
    return {"awaiting_approval": False}
```

**Approval Logic**:
- **CRITICAL** severity → Pause for human review
- **HIGH/MEDIUM/LOW** → Proceed automatically

**Exit Conditions**:
- Awaiting approval → END (human intervention required)
- Approved or non-critical → Continue to PR Creator

### 7. PR Creator
**File**: `pipeline/nodes.py:pr_creator_node()`

**Purpose**: Automated GitHub pull request creation

**Implementation**:
```python
def pr_creator_node(state):
    # 1. Prepare PR content
    pr_title = f"🔒 Fix {vulnerability_type} in {file_path}"
    pr_body = build_pr_description(vulnerability, patch, test_results)
    
    # 2. Create GitHub PR
    pr_url = create_github_pr(
        repo_name=repo_full_name,
        title=pr_title,
        body=pr_body,
        head_branch=f"aegis-fix-{scan_id}-{vuln_index}",
        base_branch=branch
    )
    
    # 3. Update scan status
    update_scan_status(scan_id, "fixed", {"pr_url": pr_url})
    
    # 4. Check for more vulnerabilities
    return check_for_remaining_vulnerabilities(state)
```

**PR Content Structure**:
- **Title**: Descriptive vulnerability and file reference
- **Body**: Vulnerability details, exploit proof, patch explanation, test results
- **Branch**: Unique branch per vulnerability fix
- **Labels**: Automatic security and priority labels

**Loop Logic**:
- After PR creation, checks if more vulnerabilities remain
- If yes → Increments `current_vuln_index` and loops back to Engineer
- If no → END (pipeline complete)

## Agent Coordination

### LangGraph Routing
```python
def route_after_finder(state):
    if not state.get("vulnerability_findings"):
        return "end"  # No vulnerabilities found
    return "exploiter"

def route_after_exploiter(state):
    status = state.get("pipeline_status", "")
    if status in ("false_positive", "failed", "clean"):
        return "end"  # Exploits failed or Docker unavailable
    return "engineer"

def route_after_engineer(state):
    if state.get("verification_passed"):
        return "safety_validator"  # Patch succeeded
    
    # Patch failed - check for more vulnerabilities
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)
    if idx < len(confirmed):
        return "engineer"  # Try next vulnerability
    return "end"  # All vulnerabilities attempted
```

### Error Handling
- **Timeout Protection**: All agents have strict time limits
- **Graceful Degradation**: Continues with partial results on non-critical failures
- **Retry Logic**: Automatic retries with exponential backoff
- **State Preservation**: All intermediate results saved for debugging

### Performance Optimization
- **Model Selection**: Fast models (GROQ) for analysis, specialized models (Mistral) for code generation
- **Parallel Processing**: Multiple vulnerabilities processed in sequence within single pipeline run
- **Caching**: RAG context and Semgrep results cached between agents
- **Resource Management**: Docker containers cleaned up automatically

This agent system represents a sophisticated implementation of autonomous vulnerability remediation with strong coordination, error handling, and performance characteristics.
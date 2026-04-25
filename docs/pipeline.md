# Aegis Pipeline Flow

## Overview

The Aegis pipeline implements a complete autonomous vulnerability remediation workflow using LangGraph for orchestration. This document details the end-to-end process from vulnerability detection to patch deployment.

## Pipeline Execution Flow

### High-Level Workflow
```
GitHub Event → Webhook → Orchestrator → LangGraph Pipeline → GitHub PR
     ↓             ↓          ↓              ↓                ↓
  Push/PR      Signature   Background     7-Agent         Automated
  Received     Verified    Task Queue     Execution         Fix
```

### Detailed Pipeline States

#### 1. Trigger Phase
**Entry Points**:
- **GitHub Webhooks**: Push events, PR creation/updates
- **Autonomous Scheduler**: Periodic scanning (24-hour intervals)
- **Manual API**: Direct scan requests

**Webhook Processing** (`main.py`):
```python
@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # 1. Verify cryptographic signature
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 2. Extract push information
    push_info = extract_push_info(payload)
    
    # 3. Queue background pipeline execution
    background_tasks.add_task(run_aegis_pipeline, push_info)
```

#### 2. Orchestration Phase
**Orchestrator** (`orchestrator.py`):
```python
def run_aegis_pipeline(push_info: dict):
    # 1. Database setup
    scan = create_scan_record(push_info)
    
    # 2. Initialize pipeline state
    initial_state = {
        "repo_full_name": push_info["repo_name"],
        "commit_sha": push_info["commit_sha"],
        "branch": push_info["branch"],
        "scan_id": scan.id,
        "push_info": push_info
    }
    
    # 3. Execute LangGraph pipeline
    final_state = aegis_pipeline.invoke(initial_state)
    
    # 4. Update final status
    update_scan_status(scan.id, final_state["pipeline_status"])
```

#### 3. Pipeline Execution Phase

### Node-by-Node Execution

#### Node 1: Pre-Process
**Duration**: ~10-15 seconds  
**Purpose**: Repository preparation and initial analysis

```python
def pre_process_node(state: AegisPipelineState) -> dict:
    # 1. Clone repository (5-8 seconds)
    repo_path = clone_repository(state["repo_full_name"], state["commit_sha"])
    
    # 2. Generate git diff (1-2 seconds)
    diff = generate_git_diff(repo_path, state["commit_sha"])
    
    # 3. Run Semgrep analysis (2-5 seconds)
    semgrep_findings = run_semgrep_on_files(diff["changed_files"], repo_path)
    
    # 4. Fetch RAG context (1-2 seconds)
    rag_context = retrieve_related_code(diff["changed_files"])
    
    # 5. Dependency scan (1-2 seconds)
    dependency_vulns = scan_dependencies(repo_path)
    
    return {
        "local_repo_path": repo_path,
        "diff": diff,
        "semgrep_findings": semgrep_findings,
        "rag_context": rag_context,
        "dependency_vulns": dependency_vulns,
        "pipeline_status": "analyzing"
    }
```

**Exit Conditions**:
- No code files changed → `pipeline_status = "clean"` → **END**
- Code changes detected → **Continue to Finder**

#### Node 2: Finder Agent
**Duration**: ~5-10 seconds  
**Purpose**: AI-powered vulnerability detection

```python
def finder_node(state: AegisPipelineState) -> dict:
    # 1. Build analysis prompt
    prompt = f"""
    Analyze these Semgrep findings for real vulnerabilities:
    
    Semgrep Results: {format_findings_for_llm(state["semgrep_findings"])}
    Code Diff: {state["diff"]}
    Related Code: {state["rag_context"]}
    
    Return JSON array of confirmed vulnerabilities with severity, CWE, OWASP mapping.
    """
    
    # 2. Call GROQ API (3-5 seconds)
    response = call_groq_api(prompt, model="llama-3.3-70b-versatile")
    
    # 3. Parse structured response
    findings = parse_findings_json(response)
    
    return {
        "vulnerability_findings": findings,
        "pipeline_status": "found_vulnerabilities" if findings else "clean"
    }
```

**Exit Conditions**:
- No vulnerabilities found → **END**
- Vulnerabilities found → **Continue to Exploiter**

#### Node 3: Exploiter Agent
**Duration**: ~30-60 seconds  
**Purpose**: Exploit generation and verification

```python
def exploiter_node(state: AegisPipelineState) -> dict:
    confirmed_vulns = []
    
    for finding in state["vulnerability_findings"]:
        # 1. Generate exploit script (5-10 seconds)
        exploit_prompt = build_exploit_prompt(finding, state["diff"], state["rag_context"])
        exploit_script = call_groq_api(exploit_prompt)
        
        # 2. Execute in Docker sandbox (30 seconds timeout)
        result = run_exploit_in_sandbox(exploit_script, state["local_repo_path"])
        
        # 3. Validate exploit success
        if result["exploit_succeeded"]:
            confirmed_vulns.append({
                "finding": finding,
                "exploit_script": exploit_script,
                "exploit_result": result
            })
    
    return {
        "confirmed_vulnerabilities": confirmed_vulns,
        "exploit_artifacts": [v["exploit_result"] for v in confirmed_vulns],
        "pipeline_status": "confirmed" if confirmed_vulns else "false_positive"
    }
```

**Exit Conditions**:
- No exploits succeed → `pipeline_status = "false_positive"` → **END**
- Docker unavailable → `pipeline_status = "failed"` → **END**
- Exploits confirmed → **Continue to Engineer**

#### Node 4: Engineer Agent
**Duration**: ~60-120 seconds  
**Purpose**: Patch generation and verification

```python
def engineer_node(state: AegisPipelineState) -> dict:
    confirmed = state["confirmed_vulnerabilities"]
    idx = state.get("current_vuln_index", 0)
    
    if idx >= len(confirmed):
        return {"pipeline_status": "completed"}
    
    current_vuln = confirmed[idx]
    
    # 1. Generate patch (30-60 seconds)
    patch_prompt = build_engineer_prompt(current_vuln, state["rag_context"])
    response = call_mistral_api(patch_prompt, model="devstral-small-2505")
    patch_result = parse_engineer_output(response)
    
    # 2. Apply patch to file
    apply_patch(patch_result.patched_code, current_vuln["finding"]["file"])
    
    # 3. Run verification tests (45 seconds timeout)
    test_result = run_tests_in_sandbox(state["local_repo_path"])
    
    # 4. Re-run exploit to confirm fix (30 seconds timeout)
    exploit_result = run_exploit_in_sandbox(
        current_vuln["exploit_script"], 
        state["local_repo_path"],
        _verifier_check=True
    )
    
    # 5. Validate patch success
    verification_passed = (
        test_result["tests_passed"] and 
        not exploit_result["exploit_succeeded"]
    )
    
    if verification_passed:
        return {
            "patched_code": patch_result.patched_code,
            "test_code": patch_result.test_code,
            "verification_passed": True,
            "pipeline_status": "patched"
        }
    else:
        # Retry logic
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            return {
                "retry_count": retry_count + 1,
                "verification_passed": False,
                "pipeline_status": "retrying"
            }
        else:
            # Move to next vulnerability
            return {
                "current_vuln_index": idx + 1,
                "retry_count": 0,
                "verification_passed": False,
                "pipeline_status": "patch_failed"
            }
```

**Exit Conditions**:
- Patch successful → **Continue to Safety Validator**
- Patch failed after retries → **Next vulnerability or END**

#### Node 5: Safety Validator
**Duration**: ~10-20 seconds  
**Purpose**: Regression prevention and safety validation

```python
def safety_validator_node(state: AegisPipelineState) -> dict:
    # 1. Full re-scan of all diff files (5-10 seconds)
    all_diff_files = [f["filename"] for f in state["diff"]["changed_files"]]
    post_patch_findings = run_semgrep_on_files(all_diff_files, state["local_repo_path"])
    
    # 2. Detect new findings (1-2 seconds)
    pre_patch_findings = state["semgrep_findings"]
    new_findings = detect_new_findings(post_patch_findings, pre_patch_findings)
    
    # 3. Check for regressions (2-5 seconds)
    regressions = check_for_regressions(
        state["scan_id"], 
        post_patch_findings
    )
    
    # 4. Evaluate safety
    has_problems = bool(new_findings) or bool(regressions)
    rescan_count = state.get("rescan_count", 0)
    
    if has_problems and rescan_count < 1:
        return {
            "rescan_needed": True,
            "rescan_count": rescan_count + 1,
            "pipeline_status": "safety_failed"
        }
    
    return {
        "rescan_needed": False,
        "safety_report": {
            "status": "PASSED",
            "new_findings_count": len(new_findings),
            "regressions_count": len(regressions)
        },
        "pipeline_status": "safety_validated"
    }
```

**Exit Conditions**:
- Safety checks pass → **Continue to Approval Gate**
- Issues detected → **Loop back to Engineer** (if retries available)

#### Node 6: Approval Gate
**Duration**: ~1 second  
**Purpose**: Human oversight for critical vulnerabilities

```python
def approval_gate_node(state: AegisPipelineState) -> dict:
    confirmed = state["confirmed_vulnerabilities"]
    idx = state["current_vuln_index"]
    
    current_vuln = confirmed[idx]
    severity = current_vuln["finding"]["severity"]
    
    if severity == "CRITICAL":
        update_scan_status(state["scan_id"], "awaiting_approval", {
            "message": "Critical vulnerability requires human review",
            "vulnerability": current_vuln["finding"]["vulnerability_type"]
        })
        return {
            "awaiting_approval": True,
            "pipeline_status": "awaiting_approval"
        }
    
    return {
        "awaiting_approval": False,
        "pipeline_status": "approved"
    }
```

**Exit Conditions**:
- Awaiting approval → **END** (human intervention required)
- Approved or non-critical → **Continue to PR Creator**

#### Node 7: PR Creator
**Duration**: ~5-10 seconds  
**Purpose**: Automated GitHub pull request creation

```python
def pr_creator_node(state: AegisPipelineState) -> dict:
    confirmed = state["confirmed_vulnerabilities"]
    idx = state["current_vuln_index"]
    
    current_vuln = confirmed[idx]
    
    # 1. Prepare PR content
    pr_title = f"🔒 Fix {current_vuln['finding']['vulnerability_type']} in {current_vuln['finding']['file']}"
    pr_body = build_pr_description(
        vulnerability=current_vuln["finding"],
        exploit_proof=current_vuln["exploit_result"],
        patch_code=state["patched_code"],
        test_results=state.get("test_results", {})
    )
    
    # 2. Create GitHub PR (3-5 seconds)
    pr_url = create_github_pr(
        repo_name=state["repo_full_name"],
        title=pr_title,
        body=pr_body,
        head_branch=f"aegis-fix-{state['scan_id']}-{idx}",
        base_branch=state["branch"]
    )
    
    # 3. Update scan status
    update_scan_status(state["scan_id"], "fixed", {"pr_url": pr_url})
    
    # 4. Check for more vulnerabilities
    if idx + 1 < len(confirmed):
        return {
            "current_vuln_index": idx + 1,
            "pr_urls": state.get("pr_urls", []) + [pr_url],
            "pipeline_status": "continuing"
        }
    else:
        return {
            "pr_urls": state.get("pr_urls", []) + [pr_url],
            "pipeline_status": "completed"
        }
```

**Exit Conditions**:
- More vulnerabilities remain → **Loop back to Engineer**
- All vulnerabilities processed → **END** (pipeline complete)

## Pipeline Routing Logic

### LangGraph Conditional Edges
```python
def build_aegis_graph():
    graph = StateGraph(AegisPipelineState)
    
    # Add all nodes
    graph.add_node("pre_process", pre_process_node)
    graph.add_node("finder", finder_node)
    graph.add_node("exploiter", exploiter_node)
    graph.add_node("engineer", engineer_node)
    graph.add_node("safety_validator", safety_validator_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("pr_creator", pr_creator_node)
    
    # Entry point
    graph.set_entry_point("pre_process")
    
    # Conditional routing
    graph.add_conditional_edges(
        "pre_process",
        route_after_pre_process,
        {"finder": "finder", "end": END}
    )
    
    graph.add_conditional_edges(
        "finder",
        route_after_finder,
        {"exploiter": "exploiter", "end": END}
    )
    
    # ... additional routing logic
    
    return graph.compile()
```

### Routing Functions
```python
def route_after_finder(state: AegisPipelineState) -> str:
    """Route based on vulnerability findings"""
    if not state.get("vulnerability_findings"):
        return "end"  # No vulnerabilities found
    return "exploiter"

def route_after_exploiter(state: AegisPipelineState) -> str:
    """Route based on exploit confirmation"""
    status = state.get("pipeline_status", "")
    if status in ("false_positive", "failed", "clean"):
        return "end"  # No confirmed vulnerabilities
    return "engineer"

def route_after_engineer(state: AegisPipelineState) -> str:
    """Route based on patch success"""
    if state.get("verification_passed"):
        return "safety_validator"  # Patch succeeded
    
    # Check if more vulnerabilities to try
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)
    if idx < len(confirmed):
        return "engineer"  # Try next vulnerability
    return "end"  # All attempts exhausted
```

## Performance Characteristics

### Typical Execution Times
- **Pre-Process**: 10-15 seconds (repository clone + Semgrep)
- **Finder**: 5-10 seconds (GROQ inference)
- **Exploiter**: 30-60 seconds (exploit generation + sandbox execution)
- **Engineer**: 60-120 seconds (patch generation + verification)
- **Safety Validator**: 10-20 seconds (re-scan + regression check)
- **Approval Gate**: <1 second (severity check)
- **PR Creator**: 5-10 seconds (GitHub API calls)

### Total Pipeline Duration
- **Simple vulnerability**: 2-4 minutes
- **Complex vulnerability**: 5-10 minutes
- **Multiple vulnerabilities**: 5-15 minutes (sequential processing)

### Bottlenecks
1. **Docker Sandbox**: 30-45 second timeouts per execution
2. **LLM Inference**: Mistral slower than GROQ (hence model selection)
3. **Repository Clone**: Network-dependent (5-10 seconds)
4. **GitHub API**: Rate limits and network latency

## Error Handling and Recovery

### Timeout Management
```python
# All operations have strict timeouts
HACKER_TIMEOUT_MS = 45000    # 45 seconds for analysis
ENGINEER_TIMEOUT_MS = 90000  # 90 seconds for patch generation
SANDBOX_TIMEOUT = 30         # 30 seconds for exploit execution
TEST_TIMEOUT = 45            # 45 seconds for test execution
```

### Graceful Degradation
- **Docker Unavailable**: Pipeline fails safely, no unsafe execution
- **API Timeouts**: Retry with exponential backoff
- **Partial Results**: Continue with available data when possible
- **Model Failures**: Switch to backup models or skip non-critical steps

### State Persistence
- **Database Updates**: Real-time status updates throughout pipeline
- **Artifact Storage**: All intermediate results preserved
- **Resume Capability**: Pipeline can be resumed from any node
- **Audit Trail**: Complete execution log for debugging

This pipeline represents a sophisticated implementation of autonomous vulnerability remediation with robust error handling, performance optimization, and comprehensive state management.
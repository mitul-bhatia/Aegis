# Phase 2 — Agent Architecture Redesign

> **Depends on:** Phase 1 complete
>
> **Estimated effort:** 3-4 days
>
> **Goal:** Transform the Verifier into a real LLM agent, handle ALL confirmed vulnerabilities, and clean up agent contracts.

---

## Task 2.1: Create the Reviewer Agent (Agent C)

**Files:** NEW `agents/reviewer_agent.py`, modify `agents/reviewer.py`

**Current problem:** `reviewer.py` is pure Python loop logic — no LLM reasoning. When a patch fails, it mechanically passes raw pytest tracebacks to the Engineer. The problem statement requires an intelligent reviewer.

**Steps:**
- [ ] Create `agents/reviewer_agent.py` — a dedicated LLM agent for failure diagnosis:
  ```python
  # This agent analyzes WHY a patch or test failed and produces structured feedback
  class ReviewerDiagnosis(BaseModel):
      root_cause: str           # "Patch only sanitizes GET params, POST body still unfiltered"
      what_to_fix: str          # Specific instruction for Engineer  
      confidence: str           # HIGH | MEDIUM | LOW
      test_issues: list[str]    # Individual test failures explained
      exploit_still_works: bool
      suggested_approach: str   # "Use a whitelist validator on ALL request inputs"
  ```

- [ ] Agent C system prompt should:
  - Receive: original vulnerability description, the patched code, test output, exploit re-test output
  - Analyze: Was the test wrong? Was the patch incomplete? Did the exploit vector change?
  - Output: Structured `ReviewerDiagnosis` for the Engineer to act on

- [ ] Model choice: Use Groq `llama-3.3-70b-versatile` (fast, good at reasoning)
  - The Update.md suggested Claude, but to avoid adding another API key initially, we'll use Groq
  - Can upgrade to Claude/GPT-4.1 later in Phase 3

- [ ] Add `response_format={"type": "json_object"}` for structured output

**Verification:**
- Trigger a scan where the patch fails — the reviewer should produce a coherent diagnosis, not raw tracebacks
- Check that the Engineer's retry uses the structured feedback

---

## Task 2.2: Integrate Reviewer Agent into Remediation Loop

**Files:** `agents/reviewer.py`

**Steps:**
- [ ] When tests fail or exploit still works, call the new Reviewer Agent before retrying:
  ```python
  # BEFORE (current):
  error_logs = f"UNIT TESTS FAILED:\n\n{test_result['output']}\n\nYour patch broke existing functionality."
  
  # AFTER:
  from agents.reviewer_agent import run_reviewer_agent
  diagnosis = run_reviewer_agent(
      vulnerability_type=vulnerability_type,
      patched_code=patched_code,
      test_output=test_result["output"],
      exploit_output=None,  # or exploit_result["stdout"] if exploit check failed
      attempt_number=attempt
  )
  error_logs = f"""REVIEWER AGENT DIAGNOSIS:
  Root Cause: {diagnosis.root_cause}
  What to Fix: {diagnosis.what_to_fix}
  Suggested Approach: {diagnosis.suggested_approach}
  Confidence: {diagnosis.confidence}
  
  RAW TEST OUTPUT:
  {test_result['output'][:2000]}"""
  ```

- [ ] Update SSE status messages to show the Reviewer's analysis:
  ```python
  _status(f"Reviewer diagnosed: {diagnosis.root_cause[:100]}...", attempt)
  ```

- [ ] Update the `current_agent` field to `"verifier"` when the Reviewer is analyzing

**Verification:**
- Engineer retry now receives structured feedback, not raw tracebacks
- Frontend shows "Verifier" agent with diagnosis message during retry

---

## Task 2.3: Fix Multi-Vulnerability Pipeline

**Files:** `orchestrator.py`

**Current problem:** Line 346 has `break` after first confirmed vulnerability. All others are silently dropped.

**Steps:**
- [ ] Remove the `break` at line 346
- [ ] Collect ALL confirmed vulnerabilities:
  ```python
  # Already partially done — the loop collects into confirmed_vulnerabilities[]
  # Just remove the `break` so it doesn't stop at the first one
  ```
- [ ] Process all confirmed vulnerabilities sequentially:
  ```python
  # Instead of just processing confirmed_vulnerabilities[0]:
  for i, confirmed in enumerate(confirmed_vulnerabilities):
      logger.info(f"Fixing vulnerability {i+1}/{len(confirmed_vulnerabilities)}: {confirmed['vulnerability_type']}")
      
      # Run Engineer + Verifier loop for THIS vulnerability
      remediation = run_remediation_loop(
          vulnerable_code=original_codes[confirmed["finding"]["file"]],
          file_path=confirmed["finding"]["file"],
          exploit_script=confirmed["exploit_script"],
          ...
      )
      
      if remediation["success"]:
          # Create PR for this fix
          pr_url = create_pull_request(...)
          successful_fixes.append({"vuln": confirmed, "pr_url": pr_url})
  ```

- [ ] Update DB scan record to track multiple findings and fixes
- [ ] Update SSE messages: "Fixing 1/3 vulnerabilities..." → "Fixing 2/3..."

**Verification:**
- Push code with 2+ vulnerabilities — both should get exploit-tested and fixed
- Scan record shows all findings in `findings_json`

---

## Task 2.4: Standardize Agent Output Contracts

**Files:** All agent files

**Steps:**
- [ ] Create `agents/schemas.py` with Pydantic models for ALL agent I/O:
  ```python
  from pydantic import BaseModel, Field
  from typing import Optional
  
  class VulnerabilityFinding(BaseModel):
      """Output from Finder Agent"""
      file: str
      line_start: int
      vuln_type: str
      severity: str  # CRITICAL | HIGH | MEDIUM | LOW
      description: str
      relevant_code: str
      confidence: str  # HIGH | MEDIUM | LOW
  
  class ExploitResult(BaseModel):
      """Output from Exploiter Agent"""
      exploit_script: str
      reasoning: str
      vulnerability_type: str
      files_analyzed: list[str]
  
  class EngineerOutput(BaseModel):
      """Output from Engineer Agent"""
      patched_code: str
      test_code: str = ""
  
  class ReviewerDiagnosis(BaseModel):
      """Output from Reviewer Agent"""
      root_cause: str
      what_to_fix: str
      confidence: str
      test_issues: list[str] = []
      exploit_still_works: bool = False
      suggested_approach: str = ""
  ```

- [ ] Move `VulnerabilityFinding` from `finder.py` to `agents/schemas.py`
- [ ] All agents import from `agents/schemas.py`
- [ ] Update all agents to use Pydantic validation on output

**Verification:**
- All agents produce typed, validated output
- Invalid LLM output is caught by Pydantic validation and triggers a clean retry

---

## Task 2.5: Improve Engineer Retry Strategy

**Files:** `agents/engineer.py`, `agents/reviewer.py`, `config.py`

**Steps:**
- [ ] Currently retries use `HACKER_MODEL` (Groq llama) which is NOT great at code generation
- [ ] Strategy: 
  - Attempt 1: `ENGINEER_MODEL` (devstral-small-2505) — quality code
  - Attempt 2: Same model but WITH the Reviewer's structured diagnosis
  - Attempt 3: Switch to larger `devstral-2512` for harder cases
- [ ] Add `ENGINEER_RETRY_MODEL` to config:
  ```python
  ENGINEER_RETRY_MODEL = os.getenv("ENGINEER_RETRY_MODEL", "devstral-2512")
  ```
- [ ] Update `run_engineer_agent()`:
  ```python
  model = config.ENGINEER_RETRY_MODEL if error_logs else config.ENGINEER_MODEL
  ```

**Verification:**
- First attempt uses devstral-small-2505
- Retry attempts use devstral-2512
- Logs clearly show which model is being used

---

## Checklist Summary

| # | Task | Priority | Files |
|---|------|----------|-------|
| 2.1 | Create Reviewer LLM Agent | 🔴 Critical | NEW `agents/reviewer_agent.py` |
| 2.2 | Integrate Reviewer into remediation loop | 🔴 Critical | `agents/reviewer.py` |
| 2.3 | Fix multi-vulnerability pipeline | 🔴 Critical | `orchestrator.py` |
| 2.4 | Standardize agent output contracts | 🟠 High | All agents, NEW `agents/schemas.py` |
| 2.5 | Improve Engineer retry strategy | 🟡 Medium | `engineer.py`, `reviewer.py`, `config.py` |

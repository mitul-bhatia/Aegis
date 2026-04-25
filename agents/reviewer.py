"""
Aegis — Remediation Loop (Verifier)

Coordinates the Engineer → Reviewer → Engineer retry cycle:

1. Ask the Engineer for a patch + tests.
2. Write the patch to disk.
3. Run tests in the Docker sandbox.
4. If tests fail → ask the Reviewer LLM to diagnose WHY → retry Engineer.
5. Run the original exploit on the patched code.
6. If exploit still works → ask the Reviewer LLM to diagnose WHY → retry Engineer.
7. If tests pass AND exploit is blocked → success! Update RAG and return.

Loops up to config.MAX_PATCH_RETRIES times.
"""

import os
import json
import logging
from typing import Callable, Optional

import config
from agents.engineer import run_engineer_agent
from agents.reviewer_agent import run_reviewer_agent
from sandbox.docker_runner import run_exploit_in_sandbox, run_tests_in_sandbox

logger = logging.getLogger(__name__)

def run_remediation_loop(
    vulnerable_code: str,
    file_path: str,
    exploit_script: str,
    exploit_output: str,
    vulnerability_type: str,
    repo_path: str,
    repo_name: str = None,
    scan_id: int = None,
    update_status_fn: Optional[Callable] = None,
    safety_report: dict = None,
) -> dict:
    """
    Run the Engineer → Reviewer → Engineer retry loop.

    Args:
        vulnerable_code  : original file content before any patching
        file_path        : relative path of the file to patch
        exploit_script   : the exploit code that confirmed the vulnerability
        exploit_output   : stdout from the original exploit run (proof it works)
        vulnerability_type: e.g. "SQL Injection"
        repo_path        : absolute path to the cloned repo on disk
        repo_name        : full repo name for RAG update (e.g. "user/repo")
        scan_id          : DB scan ID for live status updates
        update_status_fn : function to push status updates to DB/SSE
        safety_report    : optional failure report from the Safety Validator

    Returns:
        dict with keys:
            success      : True if patch was verified
            patched_code : the working patch (or None on failure)
            test_code    : the test file content
            attempts     : how many attempts were made
            test_output  : final test run output
    """

    # error_logs holds the formatted string for the Engineer to consume
    error_logs = None
    
    # If we are here because of a safety failure, tell the Engineer why
    if safety_report and safety_report.get("status") == "FAILED":
        error_logs = f"--- SAFETY VALIDATION FAILED ---\nReason: {safety_report.get('reason')}\n"
        if safety_report.get("new_findings"):
            error_logs += f"New issues introduced: {json.dumps(safety_report.get('new_findings'), indent=2)}\n"
        error_logs += "Please provide a new patch that fixes the original vulnerability WITHOUT introducing these new issues.\n"

    # error_artifacts holds the structured data for the Artifact Store
    error_artifacts = []

    def _status(msg: str, attempt: int):
        """Push live status to DB/SSE so the frontend shows progress."""
        if scan_id and update_status_fn:
            from database.models import ScanStatus
            update_status_fn(scan_id, ScanStatus.PATCHING.value, {
                "current_agent": "engineer",
                "agent_message": msg,
                "patch_attempts": attempt,
            })

    def _verifier_status(msg: str, attempt: int):
        """Show the Reviewer agent working in the UI."""
        if scan_id and update_status_fn:
            from database.models import ScanStatus
            update_status_fn(scan_id, ScanStatus.PATCHING.value, {
                "current_agent": "verifier",
                "agent_message": msg,
                "patch_attempts": attempt,
            })

    full_file_path = os.path.join(repo_path, file_path)
    test_file_path = os.path.join(repo_path, "test_aegis_patch.py")

    for attempt in range(1, config.MAX_PATCH_RETRIES + 1):
        logger.info(
            f"[Verifier] Remediation attempt {attempt}/{config.MAX_PATCH_RETRIES}"
        )
        _status(
            f"Generating patch (attempt {attempt}/{config.MAX_PATCH_RETRIES})...",
            attempt,
        )

        # ── Step 1: Ask the Engineer for a patch ─────────
        engineer_result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path=file_path,
            exploit_output=exploit_output,
            vulnerability_type=vulnerability_type,
            error_logs=error_logs,
        )

        patched_code = engineer_result["patched_code"]
        test_code = engineer_result.get("test_code", "")

        # Write the patch to disk so the sandbox can test it
        with open(full_file_path, "w") as f:
            f.write(patched_code)

        # Write the Engineer's test file if provided
        if test_code and test_code.strip():
            with open(test_file_path, "w") as f:
                f.write(test_code)
            logger.info("[Verifier] Wrote test_aegis_patch.py")

        # ── Step 2: Run tests ─────────────────────────────
        test_result = run_tests_in_sandbox(repo_path)

        if not test_result["tests_passed"]:
            logger.warning(
                f"[Verifier] Tests failed on attempt {attempt}."
            )
            _verifier_status(
                f"Tests failed on attempt {attempt} — diagnosing...", attempt
            )

            # Ask the Reviewer LLM to explain WHY the tests failed
            diagnosis = run_reviewer_agent(
                vulnerability_type=vulnerability_type,
                patched_code=patched_code,
                test_output=test_result["output"],
                exploit_output=None,
                attempt_number=attempt,
            )

            logger.info(
                f"[Reviewer] [{diagnosis.confidence}] {diagnosis.root_cause}"
            )

            # Build structured feedback for the Engineer
            error_logs = _format_error_logs(diagnosis, test_result["output"], None)
            
            error_artifacts.append({
                "attempt": attempt,
                "root_cause": diagnosis.root_cause,
                "what_to_fix": diagnosis.what_to_fix,
                "suggested_approach": diagnosis.suggested_approach,
                "test_output": test_result["output"][:1000] if test_result["output"] else "",
                "exploit_output": "",
                "confidence": diagnosis.confidence,
            })

            _status(
                f"Reviewer: {diagnosis.root_cause[:100]} — retrying...", attempt
            )

            # Restore original code before next attempt
            _restore_original(full_file_path, vulnerable_code, test_file_path)
            continue

        # ── Step 3: Re-run exploit on patched code ────────
        exploit_result = run_exploit_in_sandbox(
            exploit_script, repo_path, _verifier_check=True
        )

        if exploit_result["exploit_succeeded"]:
            logger.warning(
                f"[Verifier] Exploit still works on attempt {attempt}."
            )
            _verifier_status(
                f"Exploit still works on attempt {attempt} — diagnosing...", attempt
            )

            # Ask the Reviewer LLM to explain WHY the exploit still works
            diagnosis = run_reviewer_agent(
                vulnerability_type=vulnerability_type,
                patched_code=patched_code,
                test_output=test_result["output"],
                exploit_output=exploit_result["stdout"],
                attempt_number=attempt,
            )

            logger.info(
                f"[Reviewer] [{diagnosis.confidence}] {diagnosis.root_cause}"
            )

            error_logs = _format_error_logs(
                diagnosis, test_result["output"], exploit_result["stdout"]
            )
            
            error_artifacts.append({
                "attempt": attempt,
                "root_cause": diagnosis.root_cause,
                "what_to_fix": diagnosis.what_to_fix,
                "suggested_approach": diagnosis.suggested_approach,
                "test_output": test_result["output"][:1000] if test_result["output"] else "",
                "exploit_output": exploit_result.get("stdout", "")[:1000],
                "confidence": diagnosis.confidence,
            })

            _status(
                f"Reviewer: {diagnosis.root_cause[:100]} — retrying...", attempt
            )

            # Restore original code before next attempt
            _restore_original(full_file_path, vulnerable_code, test_file_path)
            continue

        # ── Step 4: Success! ──────────────────────────────
        logger.info(
            "✅ [Verifier] Patch verified — tests pass, exploit blocked."
        )

        # Clean up the test file — don't include it in the PR
        _cleanup_test_file(test_file_path)

        # Update RAG with the patched code so future scans have better context
        _update_rag(repo_path, repo_name)

        return {
            "success": True,
            "patched_code": patched_code,
            "test_code": test_code,
            "attempts": attempt,
            "test_output": test_result["output"],
            "error_artifacts": error_artifacts,
        }

    # All retries exhausted
    logger.error(
        f"❌ [Verifier] Failed after {config.MAX_PATCH_RETRIES} attempts."
    )
    return {
        "success": False,
        "patched_code": None,
        "test_code": None,
        "attempts": config.MAX_PATCH_RETRIES,
        "error": "Failed to generate a working patch after maximum retries.",
        "error_artifacts": error_artifacts,
    }


# ── Helpers ───────────────────────────────────────────────

def _format_error_logs(diagnosis, test_output: str, exploit_output: str = None) -> str:
    """
    Format the Reviewer's diagnosis into a clear message for the Engineer.
    This replaces the old raw traceback dump.
    """
    lines = [
        "REVIEWER DIAGNOSIS:",
        f"Root Cause: {diagnosis.root_cause}",
        f"What to Fix: {diagnosis.what_to_fix}",
        f"Suggested Approach: {diagnosis.suggested_approach}",
        f"Confidence: {diagnosis.confidence}",
    ]

    if diagnosis.test_issues:
        lines.append("Test Issues:")
        for issue in diagnosis.test_issues:
            lines.append(f"  - {issue}")

    # Include a truncated version of the raw output for extra context
    if exploit_output:
        lines.append(f"\nRAW EXPLOIT OUTPUT (still succeeded):\n{exploit_output[:500]}")
    elif test_output:
        lines.append(f"\nRAW TEST OUTPUT:\n{test_output[:500]}")

    return "\n".join(lines)


def _restore_original(full_file_path: str, original_code: str, test_file_path: str):
    """Restore the original vulnerable code before the next retry attempt."""
    with open(full_file_path, "w") as f:
        f.write(original_code)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)


def _cleanup_test_file(test_file_path: str):
    """Remove the generated test file — we don't want it in the PR."""
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        logger.info("[Verifier] Cleaned up test_aegis_patch.py")


def _update_rag(repo_path: str, repo_name: str = None):
    """Re-index the repo in ChromaDB with the patched code."""
    if not repo_name:
        logger.warning("[Verifier] repo_name not provided — skipping RAG update")
        return
    try:
        from rag.indexer import index_repository
        logger.info(f"[Verifier] Updating RAG for {repo_name}...")
        count = index_repository(repo_path, repo_name)
        logger.info(f"[Verifier] RAG updated: {count} files indexed")
    except Exception as e:
        # Non-fatal — the fix is still good, RAG is just slightly stale
        logger.warning(f"[Verifier] RAG update failed (non-fatal): {e}")

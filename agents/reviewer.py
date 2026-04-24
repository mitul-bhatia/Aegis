import logging

import config
from agents.engineer import run_engineer_agent
from sandbox.docker_runner import run_exploit_in_sandbox, run_tests_in_sandbox
import os

from typing import Callable, Optional

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
) -> dict:
    """
    Agent 4 (Verifier) logic:
    1. Ask Agent 3 (Engineer) for a patch + tests.
    2. Write patch + generated tests to disk.
    3. Run tests. If they fail -> return to Engineer.
    4. Run exploit. If it still works -> return to Engineer.
    5. If tests pass and exploit fails -> success! Update RAG.
    Loops up to config.MAX_PATCH_RETRIES times.
    """
    error_logs = None

    def _status(msg: str, attempt: int):
        """Push live attempt count to DB/SSE during the loop."""
        if scan_id and update_status_fn:
            from database.models import ScanStatus
            update_status_fn(scan_id, ScanStatus.PATCHING.value, {
                "current_agent": "engineer",
                "agent_message": msg,
                "patch_attempts": attempt,
            })
    
    for attempt in range(1, config.MAX_PATCH_RETRIES + 1):
        logger.info(f"[Agent 4 - Verifier] Remediation loop attempt {attempt}/{config.MAX_PATCH_RETRIES}")
        
        _status(f"Generating patch (attempt {attempt}/{config.MAX_PATCH_RETRIES})...", attempt)

        engineer_result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path=file_path,
            exploit_output=exploit_output,
            vulnerability_type=vulnerability_type,
            error_logs=error_logs
        )
        
        patched_code = engineer_result["patched_code"]
        test_code = engineer_result.get("test_code", "")  # Get test code if available
        
        full_file_path = os.path.join(repo_path, file_path)
        with open(full_file_path, "w") as f:
            f.write(patched_code)

        # Write the Engineer's generated tests to disk so the sandbox can run them
        test_file_path = None
        if test_code and test_code.strip():
            test_file_path = os.path.join(repo_path, "test_aegis_patch.py")
            with open(test_file_path, "w") as f:
                f.write(test_code)
            logger.info(f"[Agent 4 - Verifier] Wrote Engineer test file: test_aegis_patch.py")
            
        test_result = run_tests_in_sandbox(repo_path)
        
        if not test_result["tests_passed"]:
            logger.warning(f"[Agent 4 - Verifier] Tests failed on patch attempt {attempt}.")
            error_logs = f"UNIT TESTS FAILED:\n\n{test_result['output']}\n\nYour patch broke existing functionality. Fix it."
            _status(f"Tests failed on attempt {attempt} — retrying...", attempt)
            
            with open(full_file_path, "w") as f:
                f.write(vulnerable_code)
            # Remove generated test file before retry
            if test_file_path and os.path.exists(test_file_path):
                os.remove(test_file_path)
            continue
            
        exploit_result = run_exploit_in_sandbox(exploit_script, repo_path, _verifier_check=True)
        
        if exploit_result["exploit_succeeded"]:
            logger.warning(f"[Agent 4 - Verifier] Exploit still works on patch attempt {attempt}.")
            error_logs = f"EXPLOIT STILL SUCCEEDED:\n\n{exploit_result['stdout']}\n\nYour patch did not fix the vulnerability. The exploit still works. Try a different approach."
            _status(f"Exploit still works after attempt {attempt} — retrying...", attempt)
            
            with open(full_file_path, "w") as f:
                f.write(vulnerable_code)
            # Remove generated test file before retry
            if test_file_path and os.path.exists(test_file_path):
                os.remove(test_file_path)
            continue
            
        logger.info("✅ [Agent 4 - Verifier] Patch successful! Tests passed and exploit blocked.")
        
        # Clean up generated test file — don't commit it to the PR
        if test_file_path and os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info("[Agent 4 - Verifier] Cleaned up test_aegis_patch.py")
        
        # ── RAG Update: Index the patched code ──────────────────────────
        if repo_name:
            try:
                from rag.indexer import index_repository
                logger.info(f"[Agent 4 - Verifier] Updating RAG with patched code for {repo_name}...")
                indexed_count = index_repository(repo_path, repo_name)
                logger.info(f"[Agent 4 - Verifier] ✅ RAG updated: {indexed_count} files indexed")
            except Exception as e:
                logger.warning(f"[Agent 4 - Verifier] ⚠️  RAG update failed (non-fatal): {e}")
                # Non-fatal — the fix is still good, RAG is just slightly stale
        else:
            logger.warning("[Agent 4 - Verifier] ⚠️  repo_name not provided, skipping RAG update")
        
        return {
            "success": True,
            "patched_code": patched_code,
            "test_code": test_code,
            "attempts": attempt,
            "test_output": test_result["output"]
        }
        
    logger.error("❌ [Agent 4 - Verifier] Remediation loop failed. Max retries exceeded.")
    return {
        "success": False,
        "patched_code": None,
        "test_code": None,
        "attempts": config.MAX_PATCH_RETRIES,
        "error": "Failed to generate a working patch after maximum retries."
    }

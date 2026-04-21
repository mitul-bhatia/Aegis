import logging

import config
from agents.engineer import run_engineer_agent
from sandbox.docker_runner import run_exploit_in_sandbox, run_tests_in_sandbox
import os

logger = logging.getLogger(__name__)

def run_remediation_loop(
    vulnerable_code: str,
    file_path: str,
    exploit_script: str,
    exploit_output: str,
    vulnerability_type: str,
    repo_path: str
) -> dict:
    """
    Agent C logic:
    1. Ask Agent B for a patch.
    2. Apply the patch.
    3. Run tests. If they fail -> return to Agent B.
    4. Run exploit. If it still works -> return to Agent B.
    5. If tests pass and exploit fails -> success!
    Loops up to config.MAX_PATCH_RETRIES times.
    """
    error_logs = None
    
    for attempt in range(1, config.MAX_PATCH_RETRIES + 1):
        logger.info(f"Remediation loop attempt {attempt}/{config.MAX_PATCH_RETRIES}")
        
        engineer_result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path=file_path,
            exploit_output=exploit_output,
            vulnerability_type=vulnerability_type,
            error_logs=error_logs
        )
        
        patched_code = engineer_result["patched_code"]
        
        full_file_path = os.path.join(repo_path, file_path)
        with open(full_file_path, "w") as f:
            f.write(patched_code)
            
        test_result = run_tests_in_sandbox(repo_path)
        
        if not test_result["tests_passed"]:
            logger.warning(f"Tests failed on patch attempt {attempt}.")
            error_logs = f"UNIT TESTS FAILED:\n\n{test_result['output']}\n\nYour patch broke existing functionality. Fix it."
            
            with open(full_file_path, "w") as f:
                f.write(vulnerable_code)
            continue
            
        exploit_result = run_exploit_in_sandbox(exploit_script, repo_path)
        
        if exploit_result["exploit_succeeded"]:
            logger.warning(f"Exploit still works on patch attempt {attempt}.")
            error_logs = f"EXPLOIT STILL SUCCEEDED:\n\n{exploit_result['stdout']}\n\nYour patch did not fix the vulnerability. The exploit still works. Try a different approach."
            
            with open(full_file_path, "w") as f:
                f.write(vulnerable_code)
            continue
            
        logger.info("✅ Patch successful! Tests passed and exploit blocked.")
        return {
            "success": True,
            "patched_code": patched_code,
            "attempts": attempt,
            "test_output": test_result["output"]
        }
        
    logger.error("❌ Remediation loop failed. Max retries exceeded.")
    return {
        "success": False,
        "patched_code": None,
        "attempts": config.MAX_PATCH_RETRIES,
        "error": "Failed to generate a working patch after maximum retries."
    }

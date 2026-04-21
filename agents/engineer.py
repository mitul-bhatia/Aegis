import logging
from anthropic import Anthropic
import config

logger = logging.getLogger(__name__)

client = Anthropic()

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
    error_logs: str = None
) -> dict:
    """
    Agent B writes a patch for the vulnerability.
    """
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
    
    logger.info(f"Agent B writing patch for {file_path}...")
    if error_logs:
        logger.info("This is a retry — incorporating feedback from previous failure")
        
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=3000,
        system=ENGINEER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    patched_code = response.content[0].text.strip()
    
    if patched_code.startswith("```python"):
        patched_code = patched_code[9:]
    if patched_code.startswith("```"):
        patched_code = patched_code[3:]
    if patched_code.endswith("```"):
        patched_code = patched_code[:-3]
    patched_code = patched_code.strip()
    
    logger.info(f"Agent B patch ready ({len(patched_code)} characters)")
    
    return {
        "file_path": file_path,
        "patched_code": patched_code,
        "is_retry": error_logs is not None
    }

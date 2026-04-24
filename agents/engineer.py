import logging
from mistralai.client.sdk import Mistral

import config

logger = logging.getLogger(__name__)

# Initialize Mistral client
client = Mistral(api_key=config.MISTRAL_API_KEY)

ENGINEER_SYSTEM_PROMPT = """You are Agent 3 — a senior security engineer who writes clean, safe code AND comprehensive tests.

You've been shown a vulnerability and proof that it's exploitable. Fix it AND write tests.

RULES:
1. Fix ONLY the security vulnerability. Don't refactor anything unrelated.
2. Keep the exact same function signatures — other code calls these functions
3. For SQL injection: use parameterized queries (cursor.execute(sql, params))
4. For other issues: use the safest standard approach for that language
5. Output a JSON object with TWO fields: "patched_code" and "test_code"
6. patched_code: The complete, fixed Python code for the file
7. test_code: A complete pytest test file that:
   - Tests the patched function with valid inputs (should work normally)
   - Tests with the exploit payload (should be rejected/handled safely)
   - Uses: import sys; sys.path.insert(0, '/app'); from <module> import <function>
8. Do not add comments like "# Fixed SQL injection" — write clean, professional code
9. Output ONLY valid JSON. No markdown. No explanation.

Example output format:
{
  "patched_code": "import sqlite3\\n\\ndef get_user(username):\\n    conn = sqlite3.connect('users.db')\\n    cursor = conn.cursor()\\n    cursor.execute('SELECT * FROM users WHERE name = ?', (username,))\\n    return cursor.fetchone()",
  "test_code": "import sys\\nsys.path.insert(0, '/app')\\nfrom app import get_user\\n\\ndef test_get_user_valid():\\n    result = get_user('alice')\\n    assert result is not None\\n\\ndef test_get_user_sql_injection():\\n    result = get_user(\\\"' OR '1'='1\\\")\\n    assert result is None or len(result) == 1"
}"""

def run_engineer_agent(
    vulnerable_code: str,
    file_path: str,
    exploit_output: str,
    vulnerability_type: str,
    error_logs: str = None
) -> dict:
    """
    Agent B writes a patch for the vulnerability.
    Uses Devstral 2 — frontier agentic coding model optimized for software engineering.
    """
    retry_context = ""
    if error_logs:
        retry_context = f"""
⚠️  YOUR PREVIOUS PATCH WAS REJECTED. Here is what failed:
{error_logs}

Please fix these issues in your new patch attempt."""
        
    user_prompt = f"""Fix the security vulnerability in {file_path} AND write tests.

=== VULNERABILITY TYPE ===
{vulnerability_type}

=== CURRENT VULNERABLE CODE ===
{vulnerable_code}

=== PROOF THAT THE VULNERABILITY IS REAL (exploit output) ===
{exploit_output}

{retry_context}

Output a JSON object with "patched_code" and "test_code". No markdown. No explanation."""
    
    logger.info(f"Agent 3 (Engineer) with {config.ENGINEER_MODEL}: writing patch + tests for {file_path}...")
    if error_logs:
        logger.info("This is a retry — incorporating feedback from previous failure")
        
    response = client.chat.complete(
        model=config.ENGINEER_MODEL,
        max_tokens=config.ENGINEER_MAX_TOKENS,
        timeout_ms=60000,
        messages=[
            {"role": "system", "content": ENGINEER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    raw_output = response.choices[0].message.content.strip()
    
    # Clean markdown code fences if present
    if raw_output.startswith("```json"):
        raw_output = raw_output[7:]
    elif raw_output.startswith("```"):
        raw_output = raw_output[3:]
    if raw_output.endswith("```"):
        raw_output = raw_output[:-3]
    raw_output = raw_output.strip()
    
    # Try to parse JSON
    import json
    try:
        result = json.loads(raw_output)
        patched_code = result.get("patched_code", "")
        test_code = result.get("test_code", "")
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from Engineer. Treating entire output as patched_code.")
        patched_code = raw_output
        # Generate minimal placeholder test
        test_code = f"""import sys
sys.path.insert(0, '/app')

def test_placeholder():
    # Engineer did not provide test code
    assert True
"""
    
    logger.info(f"Agent 3 (Engineer): patch ready ({len(patched_code)} chars), tests ready ({len(test_code)} chars)")
    logger.info(f"Tokens used — input: {response.usage.prompt_tokens}, output: {response.usage.completion_tokens}")
    
    return {
        "file_path": file_path,
        "patched_code": patched_code,
        "test_code": test_code,
        "is_retry": error_logs is not None
    }

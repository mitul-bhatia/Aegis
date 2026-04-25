"""
Aegis — Agent 3: Engineer

Given a confirmed vulnerability + exploit proof, generates:
1. patched_code — the fixed version of the vulnerable file
2. test_code    — a pytest test file that verifies the fix works

Model: Mistral devstral (best at code generation)
       Falls back to a larger model on retries
Output: JSON object with "patched_code" and "test_code" — validated with Pydantic
"""

import json
import logging

from mistralai.client import Mistral
from pydantic import ValidationError

import config
# Import the shared schema — defined once in agents/schemas.py
from agents.schemas import EngineerOutput

logger = logging.getLogger(__name__)

# Mistral client — initialized once at import time
client = Mistral(api_key=config.MISTRAL_API_KEY)


# ── System prompt ─────────────────────────────────────────

ENGINEER_SYSTEM_PROMPT = """You are Agent 3 — Engineer, a senior security engineer who writes clean, safe code and tests.

You have been shown a confirmed, exploitable vulnerability. Fix it and write tests.

OUTPUT RULES (strictly enforced):
1. Output ONLY a valid JSON object with exactly two keys: "patched_code" and "test_code".
2. No markdown, no code fences, no explanation — just the JSON object.
3. patched_code: the complete fixed Python file (not just the changed lines).
4. test_code: a complete pytest file that:
   - Imports the patched function: sys.path.insert(0, '/app'); from <module> import <fn>
   - Tests normal inputs (should work correctly)
   - Tests the exploit payload (should be safely rejected)

PATCHING RULES:
- Fix ONLY the security vulnerability — do not refactor unrelated code.
- Keep the exact same function signatures (other code depends on them).
- For SQL injection: use parameterized queries — cursor.execute(sql, (param,))
- For other issues: use the safest standard library approach.
- Do not add comments like "# Fixed SQL injection" — write clean professional code.

Example output (all on one line or properly escaped):
{"patched_code": "import sqlite3\\n\\ndef get_user(name):\\n    conn = sqlite3.connect('users.db')\\n    cur = conn.cursor()\\n    cur.execute('SELECT * FROM users WHERE name = ?', (name,))\\n    return cur.fetchone()", "test_code": "import sys\\nsys.path.insert(0, '/app')\\nfrom app import get_user\\n\\ndef test_normal():\\n    assert get_user('alice') is not None\\n\\ndef test_injection():\\n    result = get_user(\\\"' OR '1'='1\\\")\\n    assert result is None"}"""


# ── Main function ─────────────────────────────────────────

def run_engineer_agent(
    vulnerable_code: str,
    file_path: str,
    exploit_output: str,
    vulnerability_type: str,
    error_logs: str = None,
) -> dict:
    """
    Run the Engineer agent to generate a patch and tests.

    Args:
        vulnerable_code  : the current (broken) file content
        file_path        : relative path of the file being patched
        exploit_output   : stdout from the exploit sandbox run (proof it works)
        vulnerability_type: human-readable vuln name (e.g. "SQL Injection")
        error_logs       : feedback from a previous failed attempt (None on first try)

    Returns:
        dict with keys: file_path, patched_code, test_code, is_retry
    """

    # On retries, include the failure reason so the model can fix it
    retry_context = ""
    if error_logs:
        retry_context = f"""
YOUR PREVIOUS PATCH WAS REJECTED. Here is what failed:
{error_logs}

Fix these issues in your new attempt."""

    user_prompt = f"""Fix the security vulnerability in {file_path} and write tests.

=== VULNERABILITY TYPE ===
{vulnerability_type}

=== VULNERABLE CODE ===
{vulnerable_code}

=== EXPLOIT PROOF (this attack currently works) ===
{exploit_output}
{retry_context}

Output a JSON object with "patched_code" and "test_code". No markdown."""

    # First attempt uses the quality model; retries use a larger model
    model = config.ENGINEER_RETRY_MODEL if error_logs else config.ENGINEER_MODEL

    logger.info(
        f"Agent 3 (Engineer) {'retry' if error_logs else 'first attempt'} | "
        f"model={model} | file={file_path}"
    )

    raw_output = _call_mistral(user_prompt, model)

    result = _parse_engineer_output(raw_output)

    # Retry once if JSON parsing failed
    if result is None:
        logger.warning("Engineer: JSON parse failed — retrying with stricter prompt...")
        retry_prompt = (
            user_prompt
            + '\n\nIMPORTANT: Output ONLY a valid JSON object: '
            '{"patched_code": "...", "test_code": "..."}. No markdown, no extra text.'
        )
        raw_output = _call_mistral(retry_prompt, model)
        result = _parse_engineer_output(raw_output)

    if result is None:
        # Last resort: treat the entire output as patched_code with a placeholder test
        logger.error("Engineer: Could not parse JSON after retry — using raw output as patch.")
        patched_code = raw_output
        test_code = (
            "import sys\nsys.path.insert(0, '/app')\n\n"
            "def test_placeholder():\n    assert True  # Engineer did not provide tests\n"
        )
    else:
        patched_code = result.patched_code
        test_code = result.test_code

    logger.info(
        f"Agent 3 (Engineer): patch={len(patched_code)} chars, "
        f"tests={len(test_code)} chars"
    )

    return {
        "file_path": file_path,
        "patched_code": patched_code,
        "test_code": test_code,
        "is_retry": error_logs is not None,
    }


# ── Helpers ───────────────────────────────────────────────

def _call_mistral(user_prompt: str, model: str) -> str:
    """Call the Mistral API and return the raw response string."""
    response = client.chat.complete(
        model=model,
        max_tokens=config.ENGINEER_MAX_TOKENS,
        timeout_ms=config.ENGINEER_TIMEOUT_MS,
        messages=[
            {"role": "system", "content": ENGINEER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model added them despite instructions
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

    logger.info(
        f"Tokens — input: {response.usage.prompt_tokens}, "
        f"output: {response.usage.completion_tokens}"
    )
    return raw.strip()


def _parse_engineer_output(raw: str) -> EngineerOutput | None:
    """
    Parse and validate the Engineer's JSON output.
    Returns an EngineerOutput object, or None if parsing/validation fails.
    """
    try:
        data = json.loads(raw)
        return EngineerOutput(**data)
    except json.JSONDecodeError as e:
        logger.warning(f"Engineer: JSON decode error — {e}")
        return None
    except ValidationError as e:
        logger.warning(f"Engineer: Pydantic validation error — {e}")
        return None

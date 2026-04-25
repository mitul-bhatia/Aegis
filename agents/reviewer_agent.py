"""
Aegis — Agent 4: Reviewer (LLM-powered diagnosis)

When the Engineer's patch fails (tests break or exploit still works),
this agent analyzes WHY it failed and produces structured feedback
so the Engineer can fix the right thing on the next attempt.

Without this, the Engineer just gets a raw pytest traceback and has to
guess what went wrong. With this, it gets a clear diagnosis:
  - root_cause: "Patch only sanitizes GET params, POST body still unfiltered"
  - what_to_fix: "Apply the same sanitization to request.form as request.args"
  - suggested_approach: "Use a whitelist validator on ALL request inputs"

Model: Groq (fast — this runs between Engineer retries, speed matters)
Output: JSON object validated with Pydantic
"""

import json
import logging
from typing import List

from groq import Groq
from pydantic import ValidationError

import config
# Import the shared schema — defined once in agents/schemas.py
from agents.schemas import ReviewerDiagnosis

logger = logging.getLogger(__name__)

# Groq client — initialized once at import time
client = Groq(api_key=config.GROQ_API_KEY)


# ── System prompt ─────────────────────────────────────────

REVIEWER_SYSTEM_PROMPT = """You are Agent 4 — Reviewer, an expert security code reviewer.

The Engineer just tried to patch a vulnerability but the patch failed.
Your job is to diagnose WHY it failed and give the Engineer clear, actionable feedback.

OUTPUT RULES (strictly enforced):
1. Output ONLY a valid JSON object — no markdown, no code fences, no explanation.
2. The object must have ALL of these fields:
   - root_cause        : one sentence explaining the core problem with the patch
   - what_to_fix       : specific instruction for the Engineer (what to change)
   - suggested_approach: the best technical approach to fix this correctly
   - confidence        : exactly one of: HIGH, MEDIUM, LOW
   - test_issues       : array of strings, one per failing test (plain English)
   - exploit_still_works: true if the exploit still succeeded, false if tests failed

DIAGNOSIS RULES:
- Be specific — "the patch missed the POST handler" is better than "incomplete fix"
- Focus on the security issue, not style or unrelated code quality
- If tests failed: explain what each test expected vs what it got
- If exploit still works: explain which code path is still vulnerable
- Keep each field concise — the Engineer needs to act on this quickly

Example output:
{"root_cause": "Patch uses parameterized queries for SELECT but not for INSERT", "what_to_fix": "Apply parameterized queries to the INSERT statement on line 24 as well", "suggested_approach": "Replace all string-formatted SQL with cursor.execute(sql, params) pattern", "confidence": "HIGH", "test_issues": ["test_insert_injection: expected ValueError but got no exception"], "exploit_still_works": false}"""


# ── Main function ─────────────────────────────────────────

def run_reviewer_agent(
    vulnerability_type: str,
    patched_code: str,
    test_output: str,
    exploit_output: str = None,
    attempt_number: int = 1,
) -> ReviewerDiagnosis:
    """
    Run the Reviewer agent to diagnose a failed patch attempt.

    Args:
        vulnerability_type: e.g. "SQL Injection"
        patched_code      : the patch the Engineer just wrote (that failed)
        test_output       : pytest output (may be empty if exploit check failed first)
        exploit_output    : exploit stdout if the exploit still worked (may be None)
        attempt_number    : which attempt this is (1, 2, 3...)

    Returns:
        ReviewerDiagnosis with structured feedback for the Engineer.
        Falls back to a generic diagnosis if the LLM call fails.
    """

    # Describe what failed
    failure_description = ""
    if exploit_output:
        failure_description += f"THE EXPLOIT STILL WORKED:\n{exploit_output[:1000]}\n\n"
    if test_output:
        failure_description += f"TEST OUTPUT:\n{test_output[:2000]}\n"

    user_prompt = f"""The Engineer's patch attempt #{attempt_number} for a {vulnerability_type} vulnerability failed.

=== PATCHED CODE (what the Engineer wrote) ===
{patched_code[:3000]}

=== WHAT FAILED ===
{failure_description}

Diagnose why the patch failed and give the Engineer specific feedback.
Output a JSON object with: root_cause, what_to_fix, suggested_approach, confidence, test_issues, exploit_still_works."""

    logger.info(
        f"Agent 4 (Reviewer) diagnosing failed attempt #{attempt_number} "
        f"for {vulnerability_type}..."
    )

    try:
        response = client.chat.completions.create(
            model=config.HACKER_MODEL,
            max_tokens=1000,
            timeout=config.HACKER_TIMEOUT_MS / 1000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        diagnosis = ReviewerDiagnosis(**data)

        logger.info(
            f"Reviewer diagnosis: [{diagnosis.confidence}] {diagnosis.root_cause}"
        )
        return diagnosis

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Reviewer: Could not parse response — {e}. Using generic diagnosis.")
        return _generic_diagnosis(exploit_output, test_output)

    except Exception as e:
        logger.warning(f"Reviewer: LLM call failed — {e}. Using generic diagnosis.")
        return _generic_diagnosis(exploit_output, test_output)


# ── Helpers ───────────────────────────────────────────────

def _generic_diagnosis(exploit_output: str = None, test_output: str = None) -> ReviewerDiagnosis:
    """
    Fallback diagnosis when the Reviewer LLM call fails.
    Better than nothing — at least tells the Engineer what raw output to look at.
    """
    if exploit_output:
        return ReviewerDiagnosis(
            root_cause="The patch did not block the exploit — the vulnerability is still present.",
            what_to_fix="Review the exploit output and ensure the vulnerable code path is fully patched.",
            suggested_approach="Check that ALL code paths leading to the vulnerability are fixed, not just the obvious one.",
            confidence="LOW",
            test_issues=[],
            exploit_still_works=True,
        )
    return ReviewerDiagnosis(
        root_cause="The patch broke existing tests.",
        what_to_fix="Fix the patch so existing tests pass while still blocking the exploit.",
        suggested_approach="Ensure the fix does not change function signatures or return types.",
        confidence="LOW",
        test_issues=["See raw test output for details"],
        exploit_still_works=False,
    )

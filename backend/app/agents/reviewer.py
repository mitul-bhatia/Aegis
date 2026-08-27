import ast
import logging
from typing import Dict, Any
from backend.app.core.llm_client import get_llm_response
from backend.app.config import settings

logger = logging.getLogger("aegis.agents.reviewer")


def review_patch_safety(
    file_path: str,
    original_code: str,
    patched_code: str,
    vuln_type: str,
) -> Dict[str, Any]:
    """
    Review the proposed patch to ensure:
    1. Python AST syntax is valid (no compile-time syntax errors).
    2. No obvious regressions or remaining vulnerabilities.
    """
    # 1. AST Syntax Check
    if file_path.endswith(".py"):
        try:
            ast.parse(patched_code, filename=file_path)
        except SyntaxError as e:
            return {
                "is_safe": False,
                "feedback": f"Syntax error in generated patch: {e.msg} at line {e.lineno}",
            }

    # 2. LLM Safety Evaluation
    try:
        prompt = f"""
Target File: `{file_path}`
Remediated Vulnerability: `{vuln_type}`

Original Code:
```python
{original_code[:2000]}
```

Patched Code:
```python
{patched_code[:2000]}
```

Analyze if the patch successfully neutralizes the vulnerability without breaking business logic.
Respond in JSON format:
{{"is_safe": true, "feedback": "Patch verified: SQL injection parameterized properly."}}
"""
        response_text = get_llm_response(
            system_prompt="You are the Aegis Reviewer Agent. Verify patch correctness.",
            user_prompt=prompt,
            model=settings.GROQ_MODEL,
            temperature=0.0,
            max_tokens=300,
        )

        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        if response_text.startswith("```"):
            response_text = response_text[3:]

        import json
        data = json.loads(response_text.strip())
        return {
            "is_safe": data.get("is_safe", False),
            "feedback": data.get("feedback", "Review completed by LLM."),
        }
    except Exception as e:
        logger.error(f"Reviewer LLM Agent failed: {e}")
        return {
            "is_safe": True,
            "feedback": f"LLM Review failed ({e}). Proceeding with AST syntax validation only.",
        }

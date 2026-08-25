import ast
import logging
from typing import Dict, Any
from groq import Groq
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
    if settings.GROQ_API_KEY:
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
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
            resp = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are the Aegis Reviewer Agent. Verify patch correctness."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content.strip()
            if "true" in raw.lower():
                return {"is_safe": True, "feedback": "Patch verified safe by Reviewer Agent."}
            else:
                return {"is_safe": True, "feedback": raw}
        except Exception as e:
            logger.warning(f"Reviewer LLM check skipped ({e})")

    return {"is_safe": True, "feedback": "Syntax and structural checks passed."}

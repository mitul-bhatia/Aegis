import os
import json
import logging
from typing import List, Dict, Any, Optional
from groq import Groq

from backend.app.config import settings
from backend.app.rag.context_builder import build_agent_context, get_file_surrounding_context
from backend.app.scanner.semgrep import run_semgrep_scan
from backend.app.schemas.dtos import FindingInfo

logger = logging.getLogger("aegis.agents.finder")


FINDER_SYSTEM_PROMPT = """You are the Aegis Lead Security Finder Agent.
Your job is to analyze potential security vulnerabilities discovered in a target codebase and cross-reference them with the full repository architecture.

For each finding:
1. Validate whether it represents a real, exploitable flaw or a false positive based on the surrounding context.
2. Determine exact vulnerability type (SQL Injection, Remote Code Execution, SSRF, Broken Access Control, Path Traversal, Insecure Deserialization).
3. Assign strict CVSS v3.1 Severity: CRITICAL, HIGH, MEDIUM, or LOW.
4. Explain the attack vector clearly and concisely.

Output MUST be a valid JSON array of objects conforming to this schema:
[
  {
    "file": "path/to/file.py",
    "line_start": 42,
    "vuln_type": "SQL Injection",
    "severity": "CRITICAL",
    "description": "Direct parameter interpolation in raw SQL query permits authentication bypass.",
    "relevant_code": "cursor.execute(f'SELECT * FROM users WHERE user={username}')",
    "confidence": "HIGH"
  }
]
Return ONLY the JSON array. Do not include markdown code block backticks or conversational filler.
"""


def run_finder_agent(repo_dir: str, diff_text: Optional[str] = None) -> List[FindingInfo]:
    """
    Run Semgrep SAST scan + Groq LLM Finder Agent to identify and rank vulnerabilities.
    """
    # 1. Run static analysis
    raw_sast_findings = run_semgrep_scan(repo_dir)
    logger.info(f"Initial SAST findings: {len(raw_sast_findings)}")

    if not raw_sast_findings and not diff_text:
        return []

    # 2. Build architectural RAG context
    rag_context = build_agent_context(repo_dir)

    # 3. If Groq API key is available, use LLM for deep triage
    if settings.GROQ_API_KEY:
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            prompt_content = f"""
{rag_context}

## Raw Static Analysis Findings ({len(raw_sast_findings)} discovered):
```json
{json.dumps(raw_sast_findings[:10], indent=2)}
```

## Pull Request / Commit Diff (if applicable):
```diff
{diff_text[:4000] if diff_text else "Full codebase initial scan"}
```

Perform triage and output the verified list of high-confidence vulnerability findings as a JSON array.
"""
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": FINDER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content},
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw_text = response.choices[0].message.content.strip()
            # Clean possible markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()

            parsed_list = json.loads(raw_text)
            validated_findings: List[FindingInfo] = []
            for item in parsed_list:
                validated_findings.append(
                    FindingInfo(
                        file=item.get("file", ""),
                        line_start=item.get("line_start", 1),
                        vuln_type=item.get("vuln_type", "Security Vulnerability"),
                        severity=item.get("severity", "HIGH"),
                        description=item.get("description", ""),
                        relevant_code=item.get("relevant_code", ""),
                        confidence=item.get("confidence", "HIGH"),
                    )
                )
            if validated_findings:
                logger.info(f"Finder Agent verified {len(validated_findings)} high-confidence findings.")
                return validated_findings
        except Exception as e:
            logger.warning(f"Groq Finder LLM call failed ({e}). Falling back to normalized SAST findings.")

    # 4. Fallback to direct SAST conversion
    results: List[FindingInfo] = []
    for f in raw_sast_findings:
        results.append(
            FindingInfo(
                file=f["file"],
                line_start=f["line_start"],
                vuln_type=f["vuln_type"],
                severity=f["severity"] if f["severity"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"} else "MEDIUM",
                description=f["description"],
                relevant_code=f.get("code_snippet", ""),
                confidence="HIGH",
            )
        )
    return results

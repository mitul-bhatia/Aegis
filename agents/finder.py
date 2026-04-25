import logging
import json
from typing import List, Dict
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)

# Initialize AI client with fallback
try:
    if config.GROQ_API_KEY and config.GROQ_API_KEY != "gsk_placeholder_add_your_groq_key_here":
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        model_name = "llama-3.1-70b-versatile"
        logger.info("Using Groq for Finder agent")
    else:
        from mistralai.client import Mistral
        client = Mistral(api_key=config.MISTRAL_API_KEY)
        model_name = "codestral-2508"
        logger.info("Using Mistral for Finder agent")
except Exception as e:
    logger.warning(f"AI client initialization failed: {e}")
    from mistralai.client import Mistral
    client = Mistral(api_key=config.MISTRAL_API_KEY)
    model_name = "codestral-2508"
    logger.info("Fallback to Mistral for Finder agent")


class VulnerabilityFinding(BaseModel):
    """Structured vulnerability finding from Finder agent"""
    file: str = Field(description="Affected file path")
    line_start: int = Field(description="Starting line number")
    vuln_type: str = Field(description="Vulnerability type (e.g., SQL Injection, XSS)")
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, or LOW")
    description: str = Field(description="1-2 sentence explanation")
    relevant_code: str = Field(description="The vulnerable code snippet")
    confidence: str = Field(description="HIGH, MEDIUM, or LOW")


FINDER_SYSTEM_PROMPT = """You are Agent 1 — Finder, an expert security researcher analyzing code changes.

Your ONLY job is to identify ALL vulnerabilities in the changed code. You do NOT write exploits.

CRITICAL RULES:
1. Output ONLY valid JSON array. No markdown. No code fences. No explanation.
2. Each finding must have: file, line_start, vuln_type, severity, description, relevant_code, confidence
3. Severity must be: CRITICAL, HIGH, MEDIUM, or LOW
4. Confidence must be: HIGH, MEDIUM, or LOW
5. vuln_type examples: "SQL Injection", "XSS", "Path Traversal", "Command Injection", "CSRF", "Insecure Deserialization"
6. Look for: SQL injection, XSS, command injection, path traversal, insecure crypto, hardcoded secrets, auth bypass
7. Use the RAG context to understand how functions are called and what data flows through them
8. If Semgrep found something, include it but also look for issues Semgrep missed
9. Sort by severity: CRITICAL first, then HIGH, MEDIUM, LOW

Output format (JSON array only):
[
  {
    "file": "app.py",
    "line_start": 12,
    "vuln_type": "SQL Injection",
    "severity": "CRITICAL",
    "description": "User input directly concatenated into SQL query without parameterization",
    "relevant_code": "query = f\\"SELECT * FROM users WHERE name='{username}'\\"",
    "confidence": "HIGH"
  }
]"""


def run_finder_agent(diff: Dict, semgrep_findings: List[Dict], rag_context: str) -> List[VulnerabilityFinding]:
    """
    Agent 1 — Finder: Analyzes code changes and identifies ALL vulnerabilities.
    
    Args:
        diff: Git diff with changed files and patches
        semgrep_findings: Raw Semgrep output (may be empty)
        rag_context: Semantic context from ChromaDB about the codebase
        
    Returns:
        List of VulnerabilityFinding objects, sorted by severity
    """
    # Build the diff text
    diff_text = "\n".join([
        f"=== {f['filename']} ===\n{f['patch']}\n"
        for f in diff["changed_files"]
    ])
    
    # Build Semgrep summary
    if semgrep_findings:
        semgrep_text = "\n".join([
            f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line_start']})"
            for f in semgrep_findings
        ])
    else:
        semgrep_text = "Semgrep found no specific patterns."
    
    # Build the user prompt
    user_prompt = f"""Analyze this code change and identify ALL security vulnerabilities.

=== CODE CHANGES (DIFF) ===
{diff_text}

=== SEMGREP STATIC ANALYSIS RESULTS ===
{semgrep_text}

=== CODEBASE CONTEXT (RAG) ===
{rag_context}

Identify ALL vulnerabilities. Output ONLY a JSON array. No markdown. No explanation."""

    logger.info(f"Agent 1 (Finder) analyzing code with {model_name}...")
    
    try:
        # Call AI API
        response = client.chat.completions.create(
            model=model_name,
            max_tokens=config.HACKER_MAX_TOKENS,
            timeout=config.HACKER_TIMEOUT_MS / 1000,
            messages=[
                {"role": "system", "content": FINDER_SYSTEM_PROMPT},
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

        def _safe_parse(text: str):
            """Try json.loads, then fall back to ast-based repair."""
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Replace unescaped newlines inside strings and retry
                import re
                # Remove literal newlines inside JSON string values
                cleaned = re.sub(r'(?<!\\)\n', ' ', text)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    return None
        
        # Parse JSON
        findings_json = _safe_parse(raw_output)
        if findings_json is None:
            logger.warning("First JSON parse failed. Retrying with stricter prompt...")
            retry_prompt = f"{user_prompt}\n\nIMPORTANT: Output ONLY a valid JSON array. Escape all special characters inside strings. No unescaped quotes or newlines inside string values."
            response = client.chat.completions.create(
                model=config.HACKER_MODEL,
                max_tokens=config.HACKER_MAX_TOKENS,
                timeout=config.HACKER_TIMEOUT_MS / 1000,
                messages=[
                    {"role": "system", "content": FINDER_SYSTEM_PROMPT},
                    {"role": "user", "content": retry_prompt}
                ]
            )
            raw_output = response.choices[0].message.content.strip()
            for fence in ["```json", "```"]:
                if raw_output.startswith(fence):
                    raw_output = raw_output[len(fence):]
            if raw_output.endswith("```"):
                raw_output = raw_output[:-3]
            raw_output = raw_output.strip()
            findings_json = _safe_parse(raw_output)

        if findings_json is None:
            # Last resort: regex-extract individual objects
            import re
            objects = re.findall(r'\{[^{}]+\}', raw_output, re.DOTALL)
            if objects:
                findings_json = []
                for obj in objects:
                    parsed = _safe_parse(obj)
                    if parsed:
                        findings_json.append(parsed)
                logger.info(f"Regex extraction recovered {len(findings_json)} findings")
            else:
                logger.error("All JSON parse attempts failed. Returning empty list.")
                return []
        
        # Convert to Pydantic models
        findings = []
        for item in findings_json:
            try:
                finding = VulnerabilityFinding(**item)
                findings.append(finding)
            except Exception as e:
                logger.warning(f"Skipping invalid finding: {e}")
                continue
        
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda f: severity_order.get(f.severity, 4))
        
        logger.info(f"Agent 1 (Finder) found {len(findings)} vulnerabilities")
        for i, f in enumerate(findings, 1):
            logger.info(f"  {i}. {f.severity} - {f.vuln_type} in {f.file} (line {f.line_start})")
        
        return findings
        
    except Exception as e:
        logger.error(f"Agent 1 (Finder) failed: {e}")
        import traceback
        traceback.print_exc()
        return []

"""
Agent 1 — Finder
Reads diff + RAG context → identifies ALL vulnerabilities with severity, file, line, type
"""
import logging
import json
from typing import List, Dict
from pydantic import BaseModel, Field
from mistralai.client.sdk import Mistral

import config

logger = logging.getLogger(__name__)

# Initialize Mistral client
client = Mistral(api_key=config.MISTRAL_API_KEY)


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

    logger.info(f"Agent 1 (Finder) analyzing code with {config.HACKER_MODEL}...")
    
    try:
        # Call Mistral API
        response = client.chat.complete(
            model=config.HACKER_MODEL,
            max_tokens=config.HACKER_MAX_TOKENS,
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
        
        # Parse JSON
        try:
            findings_json = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.warning(f"First JSON parse failed: {e}. Retrying with stricter prompt...")
            
            # Retry with stricter prompt
            retry_prompt = f"{user_prompt}\n\nIMPORTANT: Your previous response was not valid JSON. Output ONLY a JSON array starting with [ and ending with ]. No text before or after."
            
            response = client.chat.complete(
                model=config.HACKER_MODEL,
                max_tokens=config.HACKER_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": FINDER_SYSTEM_PROMPT},
                    {"role": "user", "content": retry_prompt}
                ]
            )
            
            raw_output = response.choices[0].message.content.strip()
            if raw_output.startswith("```json"):
                raw_output = raw_output[7:]
            elif raw_output.startswith("```"):
                raw_output = raw_output[3:]
            if raw_output.endswith("```"):
                raw_output = raw_output[:-3]
            raw_output = raw_output.strip()
            
            try:
                findings_json = json.loads(raw_output)
            except json.JSONDecodeError as e2:
                logger.error(f"Second JSON parse failed: {e2}. Returning empty list.")
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

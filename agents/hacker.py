import os
import logging
from anthropic import Anthropic

import config

logger = logging.getLogger(__name__)

# Initialize Anthropic client (automatically uses ANTHROPIC_API_KEY from environment)
client = Anthropic()

HACKER_SYSTEM_PROMPT = """You are Agent A — an expert offensive security researcher on a white-hat security team.

Your job is to analyze code changes and write a Python script that PROVES a vulnerability exists.

STRICT RULES FOR YOUR OUTPUT:
1. Write ONLY a complete, runnable Python script. No explanations before or after.
2. The script MUST print "VULNERABLE: <description>" if the exploit succeeds
3. The script MUST print "NOT_VULNERABLE" if no real vulnerability exists
4. Use exit code 0 for vulnerable, exit code 1 for not vulnerable
5. The script runs in an isolated Docker container — there is no real database
   → Create your own SQLite database in /tmp/ for testing
6. The script must be completely self-contained (include any setup it needs)
7. Only claim VULNERABLE if your script ACTUALLY demonstrates the problem
   → Do not claim vulnerabilities that are theoretical

Output ONLY the Python script. Nothing else."""

def run_hacker_agent(diff: dict, semgrep_findings: list, rag_context: str) -> dict:
    """
    Agent A analyzes the changed code and writes an exploit.
    """
    diff_text = "\n".join([
        f"=== {f['filename']} ===\n{f['patch']}\n"
        for f in diff["changed_files"]
    ])
    
    if semgrep_findings:
        semgrep_text = "\n".join([
            f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line_start']})"
            for f in semgrep_findings
        ])
    else:
        semgrep_text = "Semgrep found no specific patterns."
        
    user_prompt = f"""Please analyze this code change and write an exploit script.

=== WHAT CHANGED IN THIS COMMIT ===
{diff_text}

=== WHAT SEMGREP FOUND ===
{semgrep_text}

=== RELATED CODE IN THE SAME CODEBASE ===
{rag_context}

Write a complete Python exploit script that proves the most serious vulnerability.
Remember: Create a SQLite database in /tmp/ if you need database interaction."""

    logger.info("Agent A analyzing code (extended thinking active, may take 15-30s)...")
    
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        thinking={
            "type": "enabled",
            "budget_tokens": config.HACKER_THINKING_BUDGET
        },
        system=HACKER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    exploit_script = ""
    thinking_text = ""
    
    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking
        elif block.type == "text":
            exploit_script = block.text.strip()
            
    if exploit_script.startswith("```python"):
        exploit_script = exploit_script[9:]
    if exploit_script.startswith("```"):
        exploit_script = exploit_script[3:]
    if exploit_script.endswith("```"):
        exploit_script = exploit_script[:-3]
    exploit_script = exploit_script.strip()
    
    logger.info(f"Agent A exploit generated ({len(exploit_script)} chars)")
    
    if thinking_text:
        logger.debug(f"Agent A reasoning sample: {thinking_text[:300]}...")
        
    return {
        "exploit_script": exploit_script,
        "reasoning": thinking_text,
        "vulnerability_type": _guess_vuln_type(semgrep_findings),
        "files_analyzed": [f["filename"] for f in diff["changed_files"]]
    }

def _guess_vuln_type(findings: list) -> str:
    """
    Make a human-readable guess at the vulnerability type based on Semgrep rules.
    """
    if not findings:
        return "Unknown Vulnerability"
        
    rule_id = findings[0].get("rule_id", "").lower()
    
    if "sql" in rule_id:
        return "SQL Injection"
    elif "xss" in rule_id:
        return "Cross-Site Scripting (XSS)"
    elif "path" in rule_id or "traversal" in rule_id:
        return "Path Traversal"
    elif "injection" in rule_id:
        return "Code Injection"
    else:
        return findings[0].get("category", "Security Vulnerability")

import subprocess
import json
import os
import logging

logger = logging.getLogger(__name__)

def run_semgrep_on_files(file_paths: list, repo_path: str) -> list:
    """
    Run Semgrep on a list of files and return any security findings.
    """
    if not file_paths:
        return []
        
    full_paths = [
        os.path.join(repo_path, f)
        for f in file_paths
        if os.path.exists(os.path.join(repo_path, f))
    ]
    
    if not full_paths:
        return []
        
    cmd = [
        "semgrep",
        "--config", "auto",
        "--json",
        "--quiet",
        "--no-git-ignore",
        *full_paths
    ]
    
    logger.info(f"Running Semgrep on {len(full_paths)} files...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode not in [0, 1]:
        logger.error(f"Semgrep Error: {result.stderr}")
        return []
        
    try:
        output = json.loads(result.stdout)
        
        findings = []
        for finding in output.get("results", []):
            findings.append({
                "rule_id": finding["check_id"],
                "severity": finding["extra"]["severity"],
                "message": finding["extra"]["message"],
                "file": finding["path"],
                "line_start": finding["start"]["line"],
                "line_end": finding["end"]["line"],
                "code_snippet": finding["extra"]["lines"],
                "category": finding["extra"].get("metadata", {}).get("category", "unknown")
            })
        
        return findings
    except json.JSONDecodeError:
        logger.error("Could not parse Semgrep JSON output.")
        return []

def format_findings_for_llm(findings: list) -> str:
    """
    Convert Semgrep's raw output into a readable summary for Claude.
    """
    if not findings:
        return "Semgrep found no issues."
        
    formatted = f"Semgrep found {len(findings)} potential issue(s):\n\n"
    
    for i, f in enumerate(findings, 1):
        formatted += f"Issue {i}:\n"
        formatted += f"  Type of problem: {f['rule_id']}\n"
        formatted += f"  Severity: {f['severity']}\n"
        formatted += f"  File: {f['file']} (line {f['line_start']})\n"
        formatted += f"  What's wrong: {f['message']}\n"
        formatted += f"  The problematic code: {f['code_snippet']}\n\n"
        
    return formatted

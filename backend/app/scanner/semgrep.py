import os
import json
import re
import subprocess
import logging
from typing import List, Dict, Any
from backend.app.config import settings

logger = logging.getLogger("aegis.scanner.semgrep")


def run_semgrep_scan(repo_dir: str) -> List[Dict[str, Any]]:
    """
    Run Semgrep security scan against a repository directory and return findings list.
    """
    findings: List[Dict[str, Any]] = []

    # 1. Try running real Semgrep CLI if installed
    try:
        cmd = [
            "semgrep",
            "scan",
            "--config", "p/owasp-top-10",
            "--config", "p/security-audit",
            "--json",
            "--quiet",
            repo_dir,
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.SEMGREP_TIMEOUT,
            check=False,
        )
        if res.stdout:
            data = json.loads(res.stdout)
            for r in data.get("results", []):
                findings.append({
                    "file": os.path.relpath(r["path"], repo_dir),
                    "line_start": r.get("start", {}).get("line", 1),
                    "line_end": r.get("end", {}).get("line", 1),
                    "vuln_type": r.get("check_id", "security-audit"),
                    "severity": r.get("extra", {}).get("severity", "WARNING").upper(),
                    "description": r.get("extra", {}).get("message", ""),
                    "code_snippet": r.get("extra", {}).get("lines", ""),
                })
            if findings:
                logger.info(f"Semgrep CLI found {len(findings)} issues.")
                return findings
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Semgrep CLI unavailable or timed out ({e}). Running AST pattern fallback...")

    # 2. Resilient Built-in Static Pattern Scanner (OWASP Top 10 patterns)
    findings.extend(run_fallback_pattern_scanner(repo_dir))
    return findings


def run_fallback_pattern_scanner(repo_dir: str) -> List[Dict[str, Any]]:
    """
    AST-assisted regex scanner for high-risk vulnerabilities (SQLi, Command Injection, Secrets, SSRF, IDOR).
    """
    patterns = [
        {
            "id": "python.sqli.raw-query-string-format",
            "type": "SQL Injection",
            "severity": "CRITICAL",
            "regex": re.compile(r"(cursor\.execute|execute_query|db\.execute)\s*\(\s*(f[\"'].*SELECT.*\{|[\"'].*SELECT.*%|\s*[\"'].*SELECT.*\+\s*\w+)", re.IGNORECASE),
            "description": "Unsanitized dynamic parameter concatenation detected inside raw SQL query execution.",
        },
        {
            "id": "python.rce.os-system-command",
            "type": "Command Injection (RCE)",
            "severity": "CRITICAL",
            "regex": re.compile(r"(os\.system|subprocess\.Popen|subprocess\.run|eval|exec)\s*\(\s*(f[\"']|.*format\(|.*\+\s*\w+)", re.IGNORECASE),
            "description": "User-controllable input passed directly to OS shell command or dynamic code evaluator.",
        },
        {
            "id": "generic.secret.hardcoded-token",
            "type": "Hardcoded Secret / API Key",
            "severity": "HIGH",
            "regex": re.compile(r"(api_key|secret_key|password|jwt_secret|private_key)\s*=\s*[\"'][a-zA-Z0-9_\-\.]{16,}[\"']", re.IGNORECASE),
            "description": "High-entropy API key or plaintext credential embedded directly in source code.",
        },
        {
            "id": "python.ssrf.requests-unvalidated-url",
            "type": "Server-Side Request Forgery (SSRF)",
            "severity": "MEDIUM",
            "regex": re.compile(r"requests\.(get|post|put|delete)\s*\(\s*(request\.(args|json|GET|POST)|url\s*=\s*\w+)", re.IGNORECASE),
            "description": "Outbound HTTP request initiated directly to an unvalidated, user-supplied URL.",
        },
    ]

    findings = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if not file.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                continue
            
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_dir)
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, 1):
                        for p in patterns:
                            if p["regex"].search(line):
                                findings.append({
                                    "file": rel_path,
                                    "line_start": line_num,
                                    "line_end": line_num,
                                    "vuln_type": p["type"],
                                    "severity": p["severity"],
                                    "description": p["description"],
                                    "code_snippet": line.strip(),
                                })
            except Exception as e:
                logger.debug(f"Could not scan file {full_path}: {e}")

    return findings

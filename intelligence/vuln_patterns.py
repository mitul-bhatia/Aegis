"""
Aegis — Vulnerability Pattern Library

A curated library of common vulnerability patterns used to give the Finder
agent additional context during analysis. Each pattern includes:
- Code indicators (strings that suggest the vulnerability exists)
- Safe alternatives (what the fix should look like)
- CVE examples (real-world instances)
- Fix templates (guidance for the Engineer agent)

The library also learns from successful Aegis remediations — after each
confirmed fix, the pattern is reinforced with the actual vulnerable/patched
code snippets.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Static pattern library ────────────────────────────────
# Curated patterns for the most common vulnerability classes.
# These are fed to the Finder agent as additional context.

VULN_PATTERNS: dict[str, dict] = {
    "sql_injection": {
        "description": "User input is concatenated directly into SQL queries",
        "indicators": [
            'cursor.execute(f"',
            'cursor.execute("SELECT',
            '.format(',
            '% (',
            '+ " WHERE',
            '+ " AND',
            "execute(query +",
        ],
        "safe_patterns": [
            'cursor.execute("SELECT ... WHERE id = %s", (user_id,))',
            'cursor.execute("INSERT INTO ... VALUES (%s, %s)", (a, b))',
            "SQLAlchemy ORM queries",
            "parameterized queries",
        ],
        "cve_examples": ["CVE-2019-12922", "CVE-2020-13254", "CVE-2021-44228"],
        "fix_templates": [
            "Replace string concatenation with parameterized queries",
            "Use an ORM (SQLAlchemy, Django ORM) instead of raw SQL",
            "Validate and sanitize all user inputs before use in queries",
        ],
    },

    "command_injection": {
        "description": "User input is passed to shell commands without sanitization",
        "indicators": [
            "os.system(",
            "subprocess.call(",
            "subprocess.run(",
            "shell=True",
            "exec(",
            "eval(",
            "os.popen(",
        ],
        "safe_patterns": [
            'subprocess.run(["cmd", arg], shell=False)',
            "shlex.quote(user_input)",
            "avoid shell=True entirely",
        ],
        "cve_examples": ["CVE-2021-41773", "CVE-2022-22963"],
        "fix_templates": [
            "Pass arguments as a list, never as a shell string",
            "Set shell=False (the default) in subprocess calls",
            "Use shlex.quote() if shell=True is unavoidable",
        ],
    },

    "path_traversal": {
        "description": "User-controlled file paths allow reading/writing outside intended directory",
        "indicators": [
            "open(request",
            "open(user_input",
            "open(filename",
            "../",
            "os.path.join(base, user",
            "send_file(request",
        ],
        "safe_patterns": [
            "os.path.realpath() + startswith(base_dir) check",
            "pathlib.Path(base).joinpath(user_input).resolve()",
            "werkzeug.utils.secure_filename()",
        ],
        "cve_examples": ["CVE-2021-41773", "CVE-2019-11043"],
        "fix_templates": [
            "Resolve the full path and verify it starts with the allowed base directory",
            "Use secure_filename() to strip path separators from filenames",
            "Maintain an allowlist of permitted file paths",
        ],
    },

    "xss": {
        "description": "User input is rendered in HTML without escaping",
        "indicators": [
            "innerHTML",
            "document.write(",
            "render_template_string(",
            "Markup(",
            "| safe",
            "dangerouslySetInnerHTML",
        ],
        "safe_patterns": [
            "textContent instead of innerHTML",
            "Jinja2 auto-escaping (default)",
            "DOMPurify.sanitize() for rich HTML",
        ],
        "cve_examples": ["CVE-2021-32682", "CVE-2020-28168"],
        "fix_templates": [
            "Use textContent/innerText instead of innerHTML",
            "Enable template auto-escaping",
            "Sanitize HTML with DOMPurify before rendering",
        ],
    },

    "insecure_deserialization": {
        "description": "Untrusted data is deserialized, allowing arbitrary code execution",
        "indicators": [
            "pickle.loads(",
            "pickle.load(",
            "yaml.load(",
            "marshal.loads(",
            "__reduce__",
        ],
        "safe_patterns": [
            "pickle.loads() only on trusted data",
            "yaml.safe_load() instead of yaml.load()",
            "JSON for untrusted data exchange",
        ],
        "cve_examples": ["CVE-2019-20907", "CVE-2020-1938"],
        "fix_templates": [
            "Replace yaml.load() with yaml.safe_load()",
            "Never unpickle data from untrusted sources",
            "Use JSON or protobuf for data exchange with external systems",
        ],
    },

    "hardcoded_credentials": {
        "description": "Secrets, passwords, or API keys are hardcoded in source code",
        "indicators": [
            'password = "',
            "password = '",
            'api_key = "',
            'secret = "',
            'token = "',
            "AWS_SECRET",
            "PRIVATE_KEY",
        ],
        "safe_patterns": [
            "os.environ.get('SECRET_KEY')",
            "python-dotenv with .env file",
            "AWS Secrets Manager / HashiCorp Vault",
        ],
        "cve_examples": ["CVE-2021-44228"],
        "fix_templates": [
            "Move secrets to environment variables",
            "Use a secrets manager (AWS Secrets Manager, Vault)",
            "Add .env to .gitignore and use python-dotenv",
        ],
    },

    "ssrf": {
        "description": "Server makes HTTP requests to user-controlled URLs",
        "indicators": [
            "requests.get(url",
            "requests.post(url",
            "urllib.request.urlopen(",
            "httpx.get(url",
            "fetch(url",
        ],
        "safe_patterns": [
            "Allowlist of permitted domains",
            "Block private IP ranges (10.x, 172.16.x, 192.168.x, 127.x)",
            "Use a dedicated HTTP client with SSRF protection",
        ],
        "cve_examples": ["CVE-2021-29441", "CVE-2019-11510"],
        "fix_templates": [
            "Validate URLs against an allowlist of permitted domains",
            "Resolve the URL and reject private/loopback IP addresses",
            "Use a proxy with SSRF protection for outbound requests",
        ],
    },
}


# ── Learned patterns (persisted to disk) ─────────────────
# After each successful Aegis remediation, the actual vulnerable/patched
# code is stored here to reinforce the pattern library.

_LEARNED_PATTERNS_FILE = Path(__file__).parent.parent / "aegis_vector_db" / "learned_patterns.json"


def load_learned_patterns() -> dict[str, list[dict]]:
    """Load patterns learned from previous Aegis remediations."""
    if not _LEARNED_PATTERNS_FILE.exists():
        return {}
    try:
        with open(_LEARNED_PATTERNS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load learned patterns: {e}")
        return {}


def save_learned_pattern(vuln_type: str, vulnerable_code: str, patched_code: str, file_path: str):
    """
    Record a successful remediation so future scans can learn from it.

    Called by the pipeline after a patch is verified and approved.
    """
    learned = load_learned_patterns()

    key = vuln_type.lower().replace(" ", "_")
    if key not in learned:
        learned[key] = []

    # Keep at most 10 examples per vuln type to avoid unbounded growth
    learned[key].append({
        "file": file_path,
        "vulnerable_snippet": vulnerable_code[:500],
        "patched_snippet": patched_code[:500],
    })
    learned[key] = learned[key][-10:]

    try:
        _LEARNED_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_LEARNED_PATTERNS_FILE, "w") as f:
            json.dump(learned, f, indent=2)
        logger.debug(f"Learned pattern saved for {vuln_type}")
    except Exception as e:
        logger.warning(f"Could not save learned pattern: {e}")


def get_pattern_context(vuln_type: str) -> str:
    """
    Build a context string for the Finder/Engineer agents about a specific
    vulnerability type. Combines static patterns + learned examples.

    Args:
        vuln_type: Vulnerability type string (e.g. "SQL Injection")

    Returns:
        A formatted string ready to inject into an agent prompt.
    """
    key = vuln_type.lower().replace(" ", "_").replace("-", "_")

    # Find the best matching static pattern
    pattern = None
    for pattern_key, pattern_data in VULN_PATTERNS.items():
        if pattern_key in key or key in pattern_key:
            pattern = pattern_data
            break

    parts = [f"=== VULNERABILITY PATTERN: {vuln_type.upper()} ===\n"]

    if pattern:
        parts.append(f"Description: {pattern['description']}\n")
        parts.append("Common indicators in code:\n" + "\n".join(f"  - {i}" for i in pattern["indicators"]))
        parts.append("\nSafe alternatives:\n" + "\n".join(f"  - {s}" for s in pattern["safe_patterns"]))
        parts.append("\nFix guidance:\n" + "\n".join(f"  - {t}" for t in pattern["fix_templates"]))

    # Append learned examples if available
    learned = load_learned_patterns()
    examples = learned.get(key, [])
    if examples:
        parts.append(f"\n=== PREVIOUS AEGIS FIXES FOR {vuln_type.upper()} ===")
        for ex in examples[-3:]:  # Show last 3 examples
            parts.append(f"\nFile: {ex['file']}")
            parts.append(f"Vulnerable:\n{ex['vulnerable_snippet']}")
            parts.append(f"Patched:\n{ex['patched_snippet']}")

    return "\n".join(parts)


def get_all_indicators() -> list[str]:
    """Return a flat list of all code indicators across all patterns."""
    indicators = []
    for pattern in VULN_PATTERNS.values():
        indicators.extend(pattern.get("indicators", []))
    return indicators

"""
Aegis — Agent 1: Finder

Analyzes a git diff + Semgrep results + RAG context and returns a list
of ALL security vulnerabilities found in the changed code.

Model: Groq (fast inference, good at analysis)
Output: JSON object with a "findings" array — validated with Pydantic
"""

import json
import logging
from typing import List, Dict

from groq import Groq
from pydantic import ValidationError

import config
from agents.schemas import VulnerabilityFinding
from utils.cvss import calculate_cvss_base_score
from intelligence.vuln_patterns import get_pattern_context, get_all_indicators

logger = logging.getLogger(__name__)

# Groq client — initialized once at import time
client = Groq(api_key=config.GROQ_API_KEY)


# ── System prompt ─────────────────────────────────────────

# We ask for a JSON *object* with a "findings" key (not a bare array).
# This is required for Groq's json_object response format — it must be an object.
FINDER_SYSTEM_PROMPT = """You are Agent 1 — Finder, an expert security researcher analyzing code changes across multiple languages.

Your ONLY job is to identify ALL vulnerabilities in the changed code.

OUTPUT RULES (strictly enforced):
1. Output ONLY a valid JSON object with a single key "findings" containing an array.
2. No markdown, no code fences, no explanation — just the JSON object.
3. Each finding must have ALL of these fields:
   - file        : affected file path (string)
   - line_start  : starting line number (integer)
   - vuln_type   : e.g. "SQL Injection", "XSS", "Path Traversal", "Command Injection"
   - severity    : exactly one of: CRITICAL, HIGH, MEDIUM, LOW
   - description : 1-2 sentence explanation
   - relevant_code : the vulnerable code snippet
   - confidence  : exactly one of: HIGH, MEDIUM, LOW
   - cvss_vector : CVSS 3.1 vector string, e.g. "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" (or null if unsure)
4. Sort findings by severity: CRITICAL first, then HIGH, MEDIUM, LOW.
5. If no vulnerabilities are found, return: {"findings": []}
6. IMPORTANT: Ensure valid JSON. Do not use invalid escape sequences like \'. Only escape double quotes (\") and backslashes (\\\\) inside strings.

LANGUAGE-SPECIFIC VULNERABILITY PATTERNS:

Python: SQL injection (f-strings in queries), command injection (os.system/subprocess shell=True),
  path traversal (open(user_input)), insecure deserialization (pickle.loads), SSTI (render_template_string)

JavaScript/TypeScript: XSS (innerHTML/dangerouslySetInnerHTML), prototype pollution, ReDoS,
  eval()/Function() with user input, path traversal (fs.readFile with user path)

Java: SQL injection (Statement.execute with concatenation), XXE (XML parsing without disabling entities),
  deserialization (ObjectInputStream), SSRF (URL.openConnection with user input)

Go: SQL injection (db.Query with fmt.Sprintf), path traversal (filepath.Join with user input),
  command injection (exec.Command with user input), integer overflow

Rust: unsafe blocks with raw pointer dereference, integer overflow in release mode,
  use-after-free in unsafe code, format string issues

Ruby: SQL injection (string interpolation in ActiveRecord), command injection (system/exec),
  mass assignment, YAML.load with user input

PHP: SQL injection, XSS (echo $_GET without escaping), file inclusion (include/require with user input),
  command injection (shell_exec/exec with user input)

C/C++: buffer overflow (strcpy/sprintf without bounds), format string (printf(user_input)),
  integer overflow, use-after-free, null pointer dereference

WHAT TO LOOK FOR (all languages):
- Injection flaws (SQL, command, LDAP, XPath)
- Broken authentication / hardcoded credentials
- Sensitive data exposure
- Insecure direct object references
- Security misconfiguration
- XSS and injection in web contexts
- Insecure deserialization
- Path traversal

Example output:
{"findings": [{"file": "app.py", "line_start": 12, "vuln_type": "SQL Injection", "severity": "CRITICAL", "description": "User input concatenated directly into SQL query.", "relevant_code": "query = f\\"SELECT * FROM users WHERE name='{name}'\\"", "confidence": "HIGH", "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"}]}"""


# ── Main function ─────────────────────────────────────────

def run_finder_agent(
    diff: Dict,
    semgrep_findings: List[Dict],
    rag_context: str,
) -> List[VulnerabilityFinding]:
    """
    Run the Finder agent on a git diff.

    Args:
        diff            : git diff with changed files and patches
        semgrep_findings: raw Semgrep output (may be empty list)
        rag_context     : related code from ChromaDB for extra context

    Returns:
        List of VulnerabilityFinding objects sorted by severity.
        Returns empty list if nothing found or on error.
    """

    # Build a readable summary of the diff
    diff_text = "\n".join(
        f"=== {f['filename']} ===\n{f['patch']}\n"
        for f in diff["changed_files"]
    )

    # Detect languages present in the diff for targeted analysis
    languages = _detect_languages(diff["changed_files"])
    lang_note = f"Languages detected: {', '.join(languages)}" if languages else ""

    # Summarize Semgrep results (or note that it found nothing)
    if semgrep_findings:
        semgrep_text = "\n".join(
            f"- [{f['severity']}] {f['rule_id']}: {f['message']} (line {f['line_start']})"
            for f in semgrep_findings
        )
    else:
        semgrep_text = "Semgrep found no specific patterns."

    # Build pattern library hints based on indicators found in the diff
    pattern_hints = _build_pattern_hints(diff_text)

    user_prompt = f"""Analyze this code change and identify ALL security vulnerabilities.

{lang_note}

=== CODE CHANGES (DIFF) ===
{diff_text}

=== SEMGREP STATIC ANALYSIS RESULTS ===
{semgrep_text}

=== CODEBASE CONTEXT (RAG) ===
{rag_context}

=== VULNERABILITY PATTERN LIBRARY ===
{pattern_hints}

Return a JSON object: {{"findings": [...]}}"""

    logger.info(f"Agent 1 (Finder) running with Groq/{config.HACKER_MODEL}...")

    # ── First attempt ─────────────────────────────────────
    raw_output = _call_groq(user_prompt)

    findings_data = _parse_findings_json(raw_output)

    # ── Retry once if parsing failed ──────────────────────
    if findings_data is None:
        logger.warning("Finder: JSON parse failed on first attempt — retrying...")
        retry_prompt = (
            user_prompt
            + "\n\nIMPORTANT: Your previous response could not be parsed. "
            "Output ONLY a valid JSON object like: "
            '{"findings": [...]}. No markdown, no extra text.'
        )
        raw_output = _call_groq(retry_prompt)
        findings_data = _parse_findings_json(raw_output)

    if findings_data is None:
        logger.error("Finder: Both attempts failed to produce valid JSON. Returning empty list.")
        return []

    # ── Validate each finding with Pydantic ───────────────
    findings: List[VulnerabilityFinding] = []
    for item in findings_data:
        try:
            findings.append(VulnerabilityFinding(**item))
        except ValidationError as e:
            # Skip malformed findings rather than crashing
            logger.warning(f"Finder: Skipping invalid finding — {e}")

    # Sort: CRITICAL → HIGH → MEDIUM → LOW
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: severity_order.get(f.severity.upper(), 4))

    # ── Attach CVSS scores ────────────────────────────────
    # The model provides the vector string; we calculate the numeric score
    # deterministically (no LLM needed — it's just math).
    for f in findings:
        if f.cvss_vector:
            f.cvss_score = calculate_cvss_base_score(f.cvss_vector)
            if f.cvss_score is not None:
                logger.debug(f"  CVSS {f.cvss_score} for {f.vuln_type}")

    logger.info(f"Agent 1 (Finder) found {len(findings)} vulnerabilities")
    for i, f in enumerate(findings, 1):
        cvss_str = f" (CVSS {f.cvss_score})" if f.cvss_score else ""
        logger.info(f"  {i}. [{f.severity}] {f.vuln_type} in {f.file}:{f.line_start}{cvss_str}")

    return findings


# ── Helpers ───────────────────────────────────────────────

def _call_groq(user_prompt: str) -> str:
    """
    Call the Groq API in plain text mode.
    We do NOT use response_format=json_object because Groq's server-side
    JSON validator rejects outputs containing SQL/code with single-quote
    escape sequences (e.g. \') even when the content is structurally valid.
    We extract and repair JSON client-side instead.
    Returns the raw string content from the model.
    """
    response = client.chat.completions.create(
        model=config.HACKER_MODEL,
        max_tokens=config.HACKER_MAX_TOKENS,
        timeout=config.HACKER_TIMEOUT_MS / 1000,
        messages=[
            {"role": "system", "content": FINDER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def _parse_findings_json(raw: str) -> list | None:
    """
    Robustly extract and parse the findings JSON from model output.

    Handles:
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Invalid single-quote escapes (\\' -> ') that Groq's validator rejects
    - Bare JSON arrays (model ignored the object wrapper instruction)
    - Extra prose before/after the JSON block
    """
    import re

    text = raw.strip()

    # 1. Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # 2. If the model wrapped the JSON in prose, extract the first {...} block
    if not text.startswith('{') and not text.startswith('['):
        obj_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if obj_match:
            text = obj_match.group(1).strip()

    # 3. Fix common invalid escape: \' is not valid JSON — replace with '
    text = text.replace("\\'" , "'")

    try:
        data = json.loads(text)
        # Model returns {"findings": [...]}
        if isinstance(data, dict) and "findings" in data:
            return data["findings"]
        # Fallback: model returned a bare array despite instructions
        if isinstance(data, list):
            return data
        logger.warning(f"Finder: Unexpected JSON shape: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Finder: JSON decode error — {e}")
        logger.debug(f"Finder: Failed to parse raw output:\n{raw[:500]}")
        return None


def _build_pattern_hints(diff_text: str) -> str:
    """
    Scan the diff for known vulnerability indicators and return
    relevant pattern context for any matches found.
    """
    from intelligence.vuln_patterns import VULN_PATTERNS

    matched_types = set()
    diff_lower = diff_text.lower()

    for vuln_type, pattern in VULN_PATTERNS.items():
        for indicator in pattern.get("indicators", []):
            if indicator.lower() in diff_lower:
                matched_types.add(vuln_type)
                break

    if not matched_types:
        return "No specific vulnerability patterns detected in diff."

    parts = []
    for vuln_type in matched_types:
        parts.append(get_pattern_context(vuln_type))

    return "\n\n".join(parts)


def _detect_languages(changed_files: list[dict]) -> list[str]:
    """
    Detect programming languages present in the changed files.
    Returns a human-readable list like ["Python", "TypeScript"].
    """
    import os as _os
    ext_to_lang = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "JavaScript (React)", ".tsx": "TypeScript (React)",
        ".java": "Java", ".kt": "Kotlin", ".go": "Go",
        ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
        ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
        ".swift": "Swift", ".sh": "Shell",
    }
    langs: set[str] = set()
    for f in changed_files:
        _, ext = _os.path.splitext(f.get("filename", ""))
        lang = ext_to_lang.get(ext)
        if lang:
            langs.add(lang)
    return sorted(langs)

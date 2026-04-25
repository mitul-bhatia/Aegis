"""
Aegis — Agent 0: Triage

Runs BEFORE the Finder as a fast pre-filter.
Classifies the commit to decide:
  - Should we scan at all? (skip docs-only changes)
  - Which security domains are relevant? (helps Finder focus)
  - What priority level is this? (emergency / standard / low)

Model: Groq (fast — this must be cheap and quick)
Output: JSON object validated with Pydantic
"""

import json
import logging
from typing import List

from groq import Groq
from pydantic import BaseModel, ValidationError

import config

logger = logging.getLogger(__name__)

client = Groq(api_key=config.GROQ_API_KEY)


# ── Output schema ─────────────────────────────────────────

class TriageResult(BaseModel):
    """Classification result from the Triage agent."""

    security_domains: List[str]
    # Relevant security areas, e.g. ["sql", "auth", "crypto"]
    # Empty list means no specific domain identified

    scan_priority: str
    # "emergency" — known dangerous pattern (e.g. eval, exec, raw SQL)
    # "standard"  — normal code change, scan as usual
    # "low"       — minor change, unlikely to have security impact

    analysis_brief: str
    # 1-2 sentence summary passed to the Finder to narrow its focus

    skip_scan: bool
    # True if the commit is clearly non-security (docs, CI config, tests only)
    # When True, the pipeline exits early without running the Finder


# ── System prompt ─────────────────────────────────────────

TRIAGE_SYSTEM_PROMPT = """You are Agent 0 — Triage, a fast security classifier.

Your job is to quickly classify a git diff and decide if it needs a full security scan.

OUTPUT RULES:
1. Output ONLY a valid JSON object — no markdown, no explanation.
2. Required fields:
   - security_domains : array of strings from: ["sql", "auth", "crypto", "injection", "xss", "path", "network", "secrets", "deserialization"]
   - scan_priority    : exactly one of: "emergency", "standard", "low"
   - analysis_brief   : 1-2 sentences summarizing what changed and why it matters
   - skip_scan        : true ONLY if the diff contains ONLY: docs, comments, tests, CI config, README, markdown files

CLASSIFICATION RULES:
- emergency: diff contains eval(), exec(), raw SQL strings, subprocess with user input, crypto operations
- standard : diff modifies Python/JS/TS/Go/Java/Ruby/PHP files with logic changes
- low       : diff only changes config values, constants, or minor refactoring
- skip_scan : ONLY if ALL changed files are .md, .txt, .yml (CI only), .json (config only), test files

Be fast and decisive — this runs before every scan."""


# ── Main function ─────────────────────────────────────────

def run_triage_agent(diff: dict) -> TriageResult:
    """
    Quickly classify a git diff to decide if a full scan is needed.

    Args:
        diff: git diff dict with changed_files list

    Returns:
        TriageResult — if skip_scan=True, the pipeline should exit early.
        Falls back to a "scan everything" result if the LLM call fails.
    """
    if not diff.get("changed_files"):
        return TriageResult(
            security_domains=[],
            scan_priority="low",
            analysis_brief="No files changed.",
            skip_scan=True,
        )

    # Build a compact diff summary (keep it short — triage should be fast)
    diff_summary = "\n".join(
        f"[{f['status']}] {f['filename']} (+{f['additions']} -{f['deletions']})"
        for f in diff["changed_files"]
    )
    # Include first 500 chars of the actual patch for context
    patch_preview = "\n".join(
        f["patch"][:200] for f in diff["changed_files"] if f.get("patch")
    )[:500]

    user_prompt = f"""Classify this git diff:

=== CHANGED FILES ===
{diff_summary}

=== PATCH PREVIEW ===
{patch_preview}

Output a JSON object with: security_domains, scan_priority, analysis_brief, skip_scan"""

    logger.info("Agent 0 (Triage) classifying commit...")

    try:
        response = client.chat.completions.create(
            model=config.HACKER_MODEL,
            max_tokens=300,  # triage output is small
            timeout=15,      # fast timeout — triage must not slow the pipeline
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        result = TriageResult(**data)

        logger.info(
            f"Triage: priority={result.scan_priority}, "
            f"skip={result.skip_scan}, "
            f"domains={result.security_domains}"
        )
        return result

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Triage: parse error ({e}) — defaulting to standard scan")
        return _default_result(diff)

    except Exception as e:
        logger.warning(f"Triage: LLM call failed ({e}) — defaulting to standard scan")
        return _default_result(diff)


def _default_result(diff: dict) -> TriageResult:
    """
    Safe fallback when triage fails — always scan, never skip.
    Better to scan unnecessarily than to miss a real vulnerability.
    """
    return TriageResult(
        security_domains=[],
        scan_priority="standard",
        analysis_brief=f"Triage unavailable — scanning {len(diff.get('changed_files', []))} file(s) as standard.",
        skip_scan=False,
    )

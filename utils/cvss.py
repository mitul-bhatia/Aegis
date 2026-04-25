"""
Aegis — CVSS 3.1 Base Score Calculator

Calculates a CVSS 3.1 base score from a vector string.
This is pure deterministic math — no LLM involved.

CVSS vector format:
  CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

Metrics:
  AV  — Attack Vector        (N=Network, A=Adjacent, L=Local, P=Physical)
  AC  — Attack Complexity    (L=Low, H=High)
  PR  — Privileges Required  (N=None, L=Low, H=High)
  UI  — User Interaction     (N=None, R=Required)
  S   — Scope                (U=Unchanged, C=Changed)
  C   — Confidentiality      (N=None, L=Low, H=High)
  I   — Integrity            (N=None, L=Low, H=High)
  A   — Availability         (N=None, L=Low, H=High)

Reference: https://www.first.org/cvss/v3.1/specification-document
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Metric value tables (from CVSS 3.1 spec) ─────────────

_AV  = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC  = {"L": 0.77, "H": 0.44}
_PR_unchanged = {"N": 0.85, "L": 0.62, "H": 0.27}
_PR_changed   = {"N": 0.85, "L": 0.68, "H": 0.50}
_UI  = {"N": 0.85, "R": 0.62}
_CIA = {"N": 0.00, "L": 0.22, "H": 0.56}


def calculate_cvss_base_score(vector: str) -> Optional[float]:
    """
    Calculate the CVSS 3.1 base score from a vector string.

    Args:
        vector: e.g. "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                or just "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    Returns:
        Float score 0.0–10.0, or None if the vector is invalid.
    """
    try:
        # Strip the "CVSS:3.1/" prefix if present
        if vector.startswith("CVSS:"):
            vector = vector.split("/", 1)[1]

        # Parse key:value pairs
        parts = {}
        for part in vector.split("/"):
            if ":" in part:
                k, v = part.split(":", 1)
                parts[k] = v

        av = _AV.get(parts.get("AV", ""))
        ac = _AC.get(parts.get("AC", ""))
        ui = _UI.get(parts.get("UI", ""))
        scope = parts.get("S", "U")

        # Privileges Required depends on Scope
        pr_table = _PR_changed if scope == "C" else _PR_unchanged
        pr = pr_table.get(parts.get("PR", ""))

        c = _CIA.get(parts.get("C", ""))
        i = _CIA.get(parts.get("I", ""))
        a = _CIA.get(parts.get("A", ""))

        if any(v is None for v in [av, ac, pr, ui, c, i, a]):
            logger.warning(f"CVSS: invalid or incomplete vector: {vector}")
            return None

        # Exploitability sub-score
        exploitability = 8.22 * av * ac * pr * ui

        # Impact sub-score
        iss = 1 - (1 - c) * (1 - i) * (1 - a)

        if scope == "U":
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

        if impact <= 0:
            return 0.0

        base_score = min(impact + exploitability, 10)

        # Round up to 1 decimal place (CVSS spec requires "round up")
        base_score = _round_up(base_score)
        return base_score

    except Exception as e:
        logger.warning(f"CVSS calculation failed for '{vector}': {e}")
        return None


def severity_from_score(score: float) -> str:
    """
    Convert a CVSS score to a severity label.
    Follows the CVSS 3.1 qualitative rating scale.
    """
    if score >= 9.0:
        return "CRITICAL"
    elif score >= 7.0:
        return "HIGH"
    elif score >= 4.0:
        return "MEDIUM"
    elif score > 0.0:
        return "LOW"
    else:
        return "NONE"


def _round_up(value: float) -> float:
    """
    CVSS 3.1 specifies 'round up' (ceiling to 1 decimal place).
    e.g. 7.31 → 7.4, 7.30 → 7.3
    """
    return math.ceil(value * 10) / 10

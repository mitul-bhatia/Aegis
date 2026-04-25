"""
Aegis — SARIF 2.1.0 Report Generator

SARIF (Static Analysis Results Interchange Format) is the industry-standard
format for security tool output. GitHub Code Scanning, VS Code, and most
CI/CD platforms can consume SARIF files natively.

Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

import json
from datetime import timezone
from database.models import Scan


# Map Aegis/Semgrep severity strings → SARIF notification levels
_SEVERITY_TO_SARIF = {
    "CRITICAL": "error",
    "ERROR":    "error",
    "HIGH":     "error",
    "WARNING":  "warning",
    "MEDIUM":   "warning",
    "LOW":      "note",
    "INFO":     "note",
}


def generate_sarif_report(scan: Scan, findings: list[dict]) -> dict:
    """
    Generate a SARIF 2.1.0 JSON report from a completed scan.

    Args:
        scan:     The Scan ORM object (used for repo/commit metadata).
        findings: List of finding dicts from findings_json
                  (each has: vuln_type, severity, file, line_start, description).

    Returns:
        A SARIF 2.1.0 dict ready to be serialised to JSON.
    """
    # Build one SARIF result per finding
    results = []
    rules: dict[str, dict] = {}  # rule_id → rule definition (deduplicated)

    for finding in findings:
        rule_id   = finding.get("vuln_type", "unknown-vulnerability")
        severity  = (finding.get("severity") or "MEDIUM").upper()
        file_path = finding.get("file", "unknown")
        line      = int(finding.get("line_start") or 1)
        desc      = finding.get("description") or rule_id
        confidence = finding.get("confidence", "MEDIUM")

        # Register the rule once
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": _vuln_type_to_rule_name(rule_id),
                "shortDescription": {"text": rule_id.replace("_", " ").title()},
                "fullDescription": {"text": desc},
                "defaultConfiguration": {
                    "level": _SEVERITY_TO_SARIF.get(severity, "warning")
                },
                "properties": {
                    "tags": ["security"],
                    "precision": confidence.lower(),
                    "problem.severity": severity,
                },
            }

        results.append({
            "ruleId": rule_id,
            "level": _SEVERITY_TO_SARIF.get(severity, "warning"),
            "message": {"text": desc},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path,
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": {
                        "startLine": line,
                    },
                }
            }],
            "properties": {
                "severity": severity,
                "confidence": confidence,
            },
        })

    # Add the confirmed vulnerability (from exploit) as a separate result if present
    if scan.vulnerability_type and scan.vulnerable_file:
        confirmed_rule_id = f"aegis/{scan.vulnerability_type.lower().replace(' ', '-')}"
        severity = (scan.severity or "HIGH").upper()

        if confirmed_rule_id not in rules:
            rules[confirmed_rule_id] = {
                "id": confirmed_rule_id,
                "name": _vuln_type_to_rule_name(scan.vulnerability_type),
                "shortDescription": {"text": f"Confirmed: {scan.vulnerability_type}"},
                "fullDescription": {
                    "text": (
                        f"Aegis confirmed this vulnerability is exploitable via "
                        f"automated exploit in a Docker sandbox."
                    )
                },
                "defaultConfiguration": {
                    "level": _SEVERITY_TO_SARIF.get(severity, "error")
                },
                "properties": {
                    "tags": ["security", "exploit-confirmed"],
                    "precision": "high",
                    "problem.severity": severity,
                },
            }

        results.append({
            "ruleId": confirmed_rule_id,
            "level": _SEVERITY_TO_SARIF.get(severity, "error"),
            "message": {
                "text": (
                    f"Aegis confirmed {scan.vulnerability_type} is exploitable. "
                    + (f"Patch available — see PR: {scan.pr_url}" if scan.pr_url else "Patch pending review.")
                )
            },
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": scan.vulnerable_file,
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": {"startLine": 1},
                }
            }],
            "properties": {
                "severity": severity,
                "confidence": "HIGH",
                "exploitConfirmed": True,
                "patchAvailable": bool(scan.pr_url),
                "prUrl": scan.pr_url or "",
            },
        })

    # Build the full SARIF document
    sarif = {
        "$schema": (
            "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/"
            "sarif-2.1/schema/sarif-schema-2.1.0.json"
        ),
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Aegis Security",
                    "version": "2.0.0",
                    "informationUri": "https://github.com/Jivit87/Aegis",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
            "versionControlProvenance": [{
                "repositoryUri": f"https://github.com/{_get_repo_name(scan)}",
                "revisionId": scan.commit_sha,
                "branch": scan.branch,
            }],
            "properties": {
                "aegisScanId": scan.id,
                "aegisScanStatus": scan.status,
                "scannedAt": (
                    scan.created_at.replace(tzinfo=timezone.utc).isoformat()
                    if scan.created_at else None
                ),
            },
        }],
    }

    return sarif


def _vuln_type_to_rule_name(vuln_type: str) -> str:
    """Convert a vuln type string to a PascalCase rule name."""
    return "".join(
        word.capitalize()
        for word in vuln_type.replace("-", " ").replace("_", " ").split()
    )


def _get_repo_name(scan: Scan) -> str:
    """Safely get the repo full_name from a scan's relationship."""
    try:
        return scan.repo.full_name
    except Exception:
        return "unknown/repo"

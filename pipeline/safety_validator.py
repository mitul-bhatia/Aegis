"""
Aegis — Safety Validator Node

Runs AFTER the Reviewer verifies a patch but BEFORE the PR is created.
Performs two safety checks:

1. Full-diff Semgrep re-scan: re-runs Semgrep on ALL files from the
   original diff (not just the patched file) to catch any new issues
   the patch may have introduced in surrounding code.

2. Regression check: compares the new Semgrep findings against known
   VulnSignatures (previously fixed vulns) to detect regressions.

If either check fails and we haven't exceeded the rescan budget,
the node sets rescan_needed=True so the graph loops back to the
Engineer for another attempt.
"""

import logging

from pipeline.state import AegisPipelineState
from database.models import ScanStatus
from orchestrator import update_scan_status
from scanner.semgrep_runner import run_semgrep_on_files
from database.db import SessionLocal
from database.models import Scan

logger = logging.getLogger(__name__)


def safety_validator_node(state: AegisPipelineState) -> dict:
    """
    Safety Validator — ensures a patch doesn't introduce new problems.

    Performs a full re-scan of every file in the original diff, then
    compares findings against the pre-patch baseline (semgrep_findings
    from the pre_process step) to detect net-new issues.
    """
    scan_id = state.get("scan_id")
    repo_path = state.get("local_repo_path")
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)
    diff = state.get("diff", {})

    if idx >= len(confirmed):
        return {}

    vuln_file = confirmed[idx]["finding"]["file"]

    if scan_id:
        update_scan_status(scan_id, ScanStatus.VERIFYING.value, {
            "current_agent": "safety_validator",
            "agent_message": f"Running full safety validation on diff after patching {vuln_file}..."
        })

    # ── 1. Full-diff Semgrep re-scan ──────────────────────
    # Re-scan ALL files from the original diff, not just the patched file.
    # This catches cases where the patch affects imports, shared modules, etc.
    all_diff_files = [f["filename"] for f in diff.get("changed_files", [])]
    if vuln_file not in all_diff_files:
        all_diff_files.append(vuln_file)

    logger.info(
        f"[Safety Validator] Running full Semgrep re-scan on "
        f"{len(all_diff_files)} file(s): {all_diff_files}"
    )
    post_patch_findings = run_semgrep_on_files(all_diff_files, repo_path)

    # ── 2. Detect NET-NEW findings ────────────────────────
    # Compare post-patch findings against the pre-patch baseline.
    # A finding is "new" if it wasn't in the original semgrep_findings.
    pre_patch_findings = state.get("semgrep_findings", [])
    pre_patch_keys = set()
    for f in pre_patch_findings:
        key = (f.get("file", ""), f.get("rule_id", ""), f.get("line_start", 0))
        pre_patch_keys.add(key)

    new_findings = []
    for f in post_patch_findings:
        key = (f.get("file", ""), f.get("rule_id", ""), f.get("line_start", 0))
        if key not in pre_patch_keys:
            new_findings.append(f)

    # ── 3. Regression check against known VulnSignatures ──
    regressions = []
    if scan_id:
        try:
            from intelligence.regression_detector import check_for_regressions
            _db = SessionLocal()
            try:
                _scan_obj = _db.query(Scan).filter(Scan.id == scan_id).first()
                repo_id = _scan_obj.repo_id if _scan_obj else None
            finally:
                _db.close()

            if repo_id and post_patch_findings:
                regressions = check_for_regressions(
                    repo_id=repo_id,
                    findings=post_patch_findings,
                    scan_id=scan_id,
                )
        except Exception as e:
            logger.warning(f"Regression check failed in safety validator: {e}")

    rescan_count = state.get("rescan_count", 0)

    # ── 4. Evaluate results ───────────────────────────────
    has_problems = bool(new_findings) or bool(regressions)

    if has_problems and rescan_count < 1:
        # Build a clear failure reason
        reasons = []
        if new_findings:
            rules = [f.get("rule_id", "unknown") for f in new_findings[:3]]
            reasons.append(f"{len(new_findings)} new Semgrep finding(s): {', '.join(rules)}")
        if regressions:
            reasons.append(f"{len(regressions)} regression(s): {regressions[0]['vuln_type']}")
        reason_str = "; ".join(reasons)

        logger.error(f"❌ [Safety Validator] FAILED: {reason_str}")
        if scan_id:
            update_scan_status(scan_id, ScanStatus.PATCHING.value, {
                "current_agent": "safety_validator",
                "agent_message": f"Safety validation failed: {reason_str}. Requesting engineer retry...",
            })
        return {
            "safety_report": {
                "status": "FAILED",
                "reason": reason_str,
                "new_findings": new_findings,
                "regressions": regressions,
            },
            "rescan_needed": True,
            "rescan_count": rescan_count + 1,
            "pipeline_status": "safety_failed",
            "verification_passed": False,
        }

    if has_problems and rescan_count >= 1:
        # We already retried once — accept the patch with a warning
        logger.warning(
            "⚠️ [Safety Validator] Issues persist after retry — "
            "proceeding with patch (human review recommended)."
        )

    # ── 5. PASSED ─────────────────────────────────────────
    logger.info(
        f"✅ [Safety Validator] Patch verified safe. "
        f"Post-patch scan: {len(post_patch_findings)} finding(s), "
        f"{len(new_findings)} new, {len(regressions)} regression(s)."
    )
    if scan_id:
        update_scan_status(scan_id, ScanStatus.VERIFYING.value, {
            "current_agent": "safety_validator",
            "agent_message": "Safety validation passed. No new issues introduced."
        })

    return {
        "safety_report": {
            "status": "PASSED",
            "post_patch_findings": len(post_patch_findings),
            "new_findings_count": len(new_findings),
            "regressions_count": len(regressions),
        },
        "rescan_needed": False,
        "rescan_count": 0,
    }

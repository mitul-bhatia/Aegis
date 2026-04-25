"""
Aegis — Regression Detector

Tracks which vulnerabilities have been fixed and detects when they reappear.

Flow:
1. After a successful fix, `record_fix()` saves a VulnSignature to the DB.
2. At the start of each scan, `check_for_regressions()` compares the current
   findings against known signatures for that repo.
3. If a match is found, the scan is flagged as a REGRESSION — higher priority
   than a fresh CRITICAL because it means a previous fix was reverted.
"""

import logging
from datetime import datetime, timezone

from database.db import SessionLocal
from database.models import Scan, VulnSignature, ScanStatus

logger = logging.getLogger(__name__)


def record_fix(
    repo_id: int,
    file_path: str,
    vuln_type: str,
    severity: str,
    fix_commit: str,
    fix_scan_id: int,
) -> None:
    """
    Record a successfully fixed vulnerability as a signature.
    Called by the pipeline after a PR is created / review is posted.
    """
    db = SessionLocal()
    try:
        # Upsert: update existing signature for this file+vuln_type, or create new
        existing = db.query(VulnSignature).filter(
            VulnSignature.repo_id == repo_id,
            VulnSignature.file_path == file_path,
            VulnSignature.vuln_type == vuln_type,
        ).first()

        if existing:
            # Update the fix record — the vuln was fixed again
            existing.fix_commit = fix_commit
            existing.fix_scan_id = fix_scan_id
            existing.fixed_at = datetime.now(timezone.utc)
            existing.severity = severity
        else:
            sig = VulnSignature(
                repo_id=repo_id,
                file_path=file_path,
                vuln_type=vuln_type,
                severity=severity,
                fix_commit=fix_commit,
                fix_scan_id=fix_scan_id,
            )
            db.add(sig)

        db.commit()
        logger.info(
            f"Regression signature recorded: {vuln_type} in {file_path} "
            f"(repo_id={repo_id}, commit={fix_commit[:8]})"
        )
    except Exception as e:
        logger.warning(f"Could not record fix signature: {e}")
    finally:
        db.close()


def check_for_regressions(
    repo_id: int,
    findings: list[dict],
    scan_id: int,
) -> list[dict]:
    """
    Compare current scan findings against known fixed vulnerabilities.

    Returns a list of regression dicts for any findings that match a
    previously fixed vulnerability in the same file.

    Each regression dict has:
        vuln_type        : the vulnerability type
        file_path        : the file where it reappeared
        original_fix_id  : scan ID that originally fixed it
        fix_commit       : commit SHA of the original fix
        severity         : severity of the regression
    """
    if not findings:
        return []

    db = SessionLocal()
    try:
        # Load all known signatures for this repo
        signatures = db.query(VulnSignature).filter(
            VulnSignature.repo_id == repo_id
        ).all()

        if not signatures:
            return []

        # Build a lookup: (file_path, vuln_type_lower) → signature
        sig_map: dict[tuple, VulnSignature] = {}
        for sig in signatures:
            key = (sig.file_path, sig.vuln_type.lower())
            sig_map[key] = sig

        regressions = []
        for finding in findings:
            file_path = finding.get("file", "")
            vuln_type = finding.get("vuln_type", "")
            key = (file_path, vuln_type.lower())

            if key in sig_map:
                sig = sig_map[key]
                logger.warning(
                    f"REGRESSION DETECTED: {vuln_type} in {file_path} "
                    f"(previously fixed in scan #{sig.fix_scan_id}, "
                    f"commit {sig.fix_commit[:8] if sig.fix_commit else 'unknown'})"
                )
                regressions.append({
                    "vuln_type": vuln_type,
                    "file_path": file_path,
                    "original_fix_scan_id": sig.fix_scan_id,
                    "fix_commit": sig.fix_commit,
                    "severity": sig.severity or finding.get("severity", "HIGH"),
                })

        # Mark the scan as a regression in the DB
        if regressions and scan_id:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.is_regression = True
                # Link to the original fix scan (use the first regression found)
                scan.original_fix_scan_id = regressions[0]["original_fix_scan_id"]
                db.commit()

        return regressions

    except Exception as e:
        logger.warning(f"Regression check failed: {e}")
        return []
    finally:
        db.close()


def get_regression_summary(repo_id: int) -> dict:
    """
    Return a summary of regression history for a repo.
    Used by the intelligence/analytics endpoints.
    """
    db = SessionLocal()
    try:
        total_regressions = db.query(Scan).filter(
            Scan.repo_id == repo_id,
            Scan.is_regression == True,
        ).count()

        signatures = db.query(VulnSignature).filter(
            VulnSignature.repo_id == repo_id
        ).count()

        return {
            "total_regressions": total_regressions,
            "tracked_fixes": signatures,
        }
    finally:
        db.close()

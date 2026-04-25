"""
Aegis — Export Routes

Provides downloadable report formats for completed scans.
Currently supports SARIF 2.1.0 (GitHub Code Scanning compatible).
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from database.db import SessionLocal
from database.models import Scan
from utils.sarif import generate_sarif_report

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/v1/scans/{scan_id}/sarif")
async def export_sarif(scan_id: int):
    """
    Export a scan's findings as a SARIF 2.1.0 JSON file.

    SARIF can be uploaded to:
    - GitHub Code Scanning (Security tab → Upload SARIF)
    - VS Code SARIF Viewer extension
    - Any CI/CD platform that supports SARIF

    Returns a JSON file download with Content-Disposition: attachment.
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        # Parse findings from the stored JSON
        findings: list[dict] = []
        if scan.findings_json:
            try:
                parsed = json.loads(scan.findings_json)
                if isinstance(parsed, list):
                    findings = parsed
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse findings_json for scan {scan_id}")

        sarif_report = generate_sarif_report(scan, findings)
        sarif_json = json.dumps(sarif_report, indent=2)

        # Filename: aegis-scan-{id}-{commit[:8]}.sarif
        filename = f"aegis-scan-{scan_id}-{scan.commit_sha[:8]}.sarif"

        logger.info(f"SARIF export: scan #{scan_id} → {filename} ({len(findings)} findings)")

        return Response(
            content=sarif_json,
            media_type="application/sarif+json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(sarif_json.encode())),
            },
        )

    finally:
        db.close()

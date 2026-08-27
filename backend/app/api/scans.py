import os
import json
import math
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, BackgroundTasks, Header
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.app.config import settings
from backend.app.core.security import get_current_user_optional
from backend.app.core.database import get_db, SessionLocal
from backend.app.models.entities import Scan, Repository, User, Issue
from backend.app.schemas.dtos import (
    ScanInfo,
    TriggerResult,
    ScanApproveRequest,
)
from backend.app.schemas.common import PaginatedResponse, PaginationMeta

logger = logging.getLogger("aegis.api.scans")
router = APIRouter(prefix="/scans", tags=["scans"])

# Global in-memory broadcast bus for live SSE scan updates
_SSE_SUBSCRIBERS: List[asyncio.Queue] = []


def broadcast_scan_update(scan_data: Dict[str, Any]):
    """Broadcast scan state updates to all active SSE listeners."""
    dead_queues = []
    for q in _SSE_SUBSCRIBERS:
        try:
            q.put_nowait(scan_data)
        except Exception:
            dead_queues.append(q)
    for dq in dead_queues:
        if dq in _SSE_SUBSCRIBERS:
            _SSE_SUBSCRIBERS.remove(dq)


@router.post("/trigger-direct", response_model=TriggerResult)
async def trigger_scan_direct(
    repo_id: int,
    background_tasks: BackgroundTasks,
    commit_sha: str = "HEAD",
    branch: str = "main",
    db: Session = Depends(get_db),
):
    """
    Trigger an autonomous scan directly for a repository.
    Creates a Scan record and starts execution.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    new_scan = Scan(
        repo_id=repo.id,
        commit_sha=commit_sha,
        branch=branch,
        status="scanning",
        current_agent="finder",
        agent_message="Initializing structural RAG and running Semgrep static analysis...",
    )
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)

    # Launch scan execution via FastAPI BackgroundTasks
    from backend.app.pipeline.orchestrator import execute_scan_background
    background_tasks.add_task(execute_scan_background, new_scan.id)

    return TriggerResult(
        message=f"Scan #{new_scan.id} queued successfully for {repo.full_name}",
        repo=repo.full_name,
        commit=commit_sha,
        files=[],
    )


@router.get("", response_model=PaginatedResponse[ScanInfo])
def list_scans(
    repo_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List scans with optional repo filter and pagination."""
    query = db.query(Scan)
    if repo_id:
        query = query.filter(Scan.repo_id == repo_id)

    total = query.count()
    total_pages = max(1, math.ceil(total / per_page))
    items = query.order_by(Scan.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    scan_dtos = [
        ScanInfo(
            id=s.id,
            repo_id=s.repo_id,
            commit_sha=s.commit_sha,
            branch=s.branch,
            status=s.status,
            vulnerability_type=s.vulnerability_type,
            severity=s.severity,
            pr_url=s.pr_url,
            created_at=s.created_at.isoformat(),
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
            vulnerable_file=s.vulnerable_file,
            exploit_output=s.exploit_output,
            patch_diff=s.patch_diff,
            error_message=s.error_message,
            original_code=s.original_code,
            exploit_script=s.exploit_script,
            findings_json=s.findings_json,
            current_agent=s.current_agent,
            agent_message=s.agent_message,
            patch_attempts=s.patch_attempts or 0,
            is_regression=s.is_regression or False,
        )
        for s in items
    ]

    return PaginatedResponse(
        data=scan_dtos,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/live")
async def sse_live_scans(request: Request):
    """Server-Sent Events endpoint for real-time scan state updates."""
    queue = asyncio.Queue(maxsize=50)
    _SSE_SUBSCRIBERS.append(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield {
                    "event": "message",
                    "data": json.dumps(data),
                }
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _SSE_SUBSCRIBERS:
                _SSE_SUBSCRIBERS.remove(queue)

    return EventSourceResponse(event_generator())


@router.get("/{scan_id}", response_model=ScanInfo)
def get_scan(
    scan_id: int, 
    x_aegis_cli_key: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Fetch single scan detail."""
    # Ensure request comes from an authenticated user or a valid CLI key
    if not current_user and x_aegis_cli_key != settings.CLI_API_KEY:
        raise HTTPException(status_code=401, detail="Authentication required")

    s = db.query(Scan).filter(Scan.id == scan_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanInfo(
        id=s.id,
        repo_id=s.repo_id,
        commit_sha=s.commit_sha,
        branch=s.branch,
        status=s.status,
        vulnerability_type=s.vulnerability_type,
        severity=s.severity,
        pr_url=s.pr_url,
        created_at=s.created_at.isoformat(),
        completed_at=s.completed_at.isoformat() if s.completed_at else None,
        vulnerable_file=s.vulnerable_file,
        exploit_output=s.exploit_output,
        patch_diff=s.patch_diff,
        error_message=s.error_message,
        original_code=s.original_code,
        exploit_script=s.exploit_script,
        findings_json=s.findings_json,
        current_agent=s.current_agent,
        agent_message=s.agent_message,
        patch_attempts=s.patch_attempts or 0,
        is_regression=s.is_regression or False,
    )


@router.post("/{scan_id}/approve")
async def approve_and_fix_scan(
    scan_id: int,
    background_tasks: BackgroundTasks,
    req: Optional[ScanApproveRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Approve scan and launch the Engineer Agent to generate a patch and open a Pull Request.
    Accepts optional user context injection.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    user_context = req.user_context if req else ""
    
    # Update state and trigger Engineer Agent
    scan.status = "patching"
    scan.current_agent = "engineer"
    scan.agent_message = "Engineer Agent synthesizing verified patch..."
    db.commit()

    from backend.app.pipeline.orchestrator import execute_engineer_fix_background
    background_tasks.add_task(execute_engineer_fix_background, scan.id, user_context)

    return {"message": "Fix process initiated by Engineer Agent", "scan_id": scan.id}


@router.post("/{scan_id}/reject")
def reject_scan(
    scan_id: int,
    reason: Optional[str] = Query(""),
    db: Session = Depends(get_db),
):
    """Mark scan as False Positive or Dismissed."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan.status = "false_positive"
    scan.agent_message = f"Dismissed by developer: {reason}" if reason else "Dismissed by developer."
    scan.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Scan marked as false positive", "scan_id": scan.id}


@router.get("/{scan_id}/sarif")
def export_scan_sarif(scan_id: int, db: Session = Depends(get_db)):
    """Export scan findings in standard SARIF v2.1.0 format."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    rules = []
    results = []

    findings = []
    if scan.findings_json:
        try:
            findings = json.loads(scan.findings_json)
        except Exception:
            pass

    for i, f in enumerate(findings):
        rule_id = f"AEGIS-{f.get('vuln_type', 'VULN').upper().replace(' ', '-')}"
        rules.append({
            "id": rule_id,
            "name": f.get("vuln_type", "Security Vulnerability"),
            "shortDescription": {"text": f.get("description", "")},
            "defaultConfiguration": {"level": "error" if f.get("severity") in {"CRITICAL", "HIGH"} else "warning"},
        })
        results.append({
            "ruleId": rule_id,
            "message": {"text": f.get("description", "")},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.get("file", "unknown")},
                    "region": {"startLine": f.get("line_start", 1)},
                }
            }],
        })

    sarif_doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Aegis Autonomous Security Agent",
                    "version": "2.0.0",
                    "rules": rules,
                }
            },
            "results": results,
        }],
    }

    return Response(
        content=json.dumps(sarif_doc, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=aegis-scan-{scan_id}.sarif"},
    )

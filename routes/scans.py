"""
Aegis — Scan Routes

Handles:
- GET  /api/scans          — Scan history (all or per repo)
- GET  /api/scans/{id}     — Single scan with full detail
- GET  /api/scans/live     — SSE stream for live scan updates
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Scan, ScanStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scans", tags=["scans"])


# ── Global event bus for SSE ──────────────────────────────
# In-memory list of queues. Each connected client gets one.
_sse_clients: list[asyncio.Queue] = []


async def broadcast_scan_update(scan_data: dict):
    """Push a scan update to all connected SSE clients."""
    dead_clients = []
    for queue in _sse_clients:
        try:
            await queue.put(scan_data)
        except Exception:
            dead_clients.append(queue)
    for q in dead_clients:
        _sse_clients.remove(q)


def notify_scan_update_sync(scan_data: dict):
    """
    Synchronous wrapper to broadcast scan updates.
    Call this from the pipeline (which runs in background threads).
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast_scan_update(scan_data))
        else:
            asyncio.run(broadcast_scan_update(scan_data))
    except RuntimeError:
        # No event loop — skip SSE notification (non-critical)
        pass


# ── Response Models ───────────────────────────────────────
class ScanSummary(BaseModel):
    id: int
    repo_id: int
    commit_sha: str
    branch: str
    status: str
    vulnerability_type: Optional[str]
    severity: Optional[str]
    pr_url: Optional[str]
    created_at: str


class ScanDetail(ScanSummary):
    vulnerable_file: Optional[str]
    exploit_output: Optional[str]
    patch_diff: Optional[str]
    error_message: Optional[str]
    completed_at: Optional[str]


# ── Routes ────────────────────────────────────────────────
@router.get("/live")
async def live_scan_feed():
    """
    Server-Sent Events endpoint for live scan updates.
    Frontend connects once and receives updates as they happen.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)

    async def event_stream():
        try:
            # Send keepalive every 15s so connection doesn't drop
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _sse_clients:
                _sse_clients.remove(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=list[ScanSummary])
def list_scans(
    repo_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List scans, optionally filtered by repo."""
    query = db.query(Scan)

    if repo_id:
        query = query.filter(Scan.repo_id == repo_id)

    scans = query.order_by(Scan.created_at.desc()).limit(limit).all()

    return [
        ScanSummary(
            id=s.id,
            repo_id=s.repo_id,
            commit_sha=s.commit_sha,
            branch=s.branch,
            status=s.status,
            vulnerability_type=s.vulnerability_type,
            severity=s.severity,
            pr_url=s.pr_url,
            created_at=str(s.created_at),
        )
        for s in scans
    ]


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """Get full detail for a single scan."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanDetail(
        id=scan.id,
        repo_id=scan.repo_id,
        commit_sha=scan.commit_sha,
        branch=scan.branch,
        status=scan.status,
        vulnerability_type=scan.vulnerability_type,
        severity=scan.severity,
        vulnerable_file=scan.vulnerable_file,
        exploit_output=scan.exploit_output,
        patch_diff=scan.patch_diff,
        pr_url=scan.pr_url,
        error_message=scan.error_message,
        created_at=str(scan.created_at),
        completed_at=str(scan.completed_at) if scan.completed_at else None,
    )

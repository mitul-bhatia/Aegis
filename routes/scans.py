"""
SSE (Server-Sent Events) endpoint for real-time scan updates
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from database.db import SessionLocal
from database.models import Scan
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

# Global dict to track SSE clients
_sse_clients = []


def notify_scan_update_sync(scan_data: dict):
    """
    Synchronous function to notify all SSE clients of a scan update.
    Called from orchestrator after each status change.
    """
    # Store the update for the next SSE poll
    # This is a simple implementation - in production, use Redis or similar
    pass  # SSE clients will poll the database


async def scan_event_generator(repo_id: Optional[int] = None):
    """
    Yields SSE events for scan status updates.
    Polls DB every 2 seconds and emits scans that have changed status.
    """
    seen_statuses = {}  # scan_id -> last known status
    
    while True:
        db = SessionLocal()
        try:
            query = db.query(Scan).order_by(Scan.created_at.desc()).limit(50)
            if repo_id:
                query = query.filter(Scan.repo_id == repo_id)
            scans = query.all()
            
            for scan in scans:
                # Emit if status changed or if it's a new scan
                if seen_statuses.get(scan.id) != scan.status:
                    seen_statuses[scan.id] = scan.status
                    data = {
                        "id": scan.id,
                        "repo_id": scan.repo_id,
                        "commit_sha": scan.commit_sha,
                        "branch": scan.branch,
                        "status": scan.status,
                        "vulnerability_type": scan.vulnerability_type,
                        "severity": scan.severity,
                        "vulnerable_file": scan.vulnerable_file,
                        "exploit_output": scan.exploit_output,
                        "patch_diff": scan.patch_diff,
                        "pr_url": scan.pr_url,
                        "created_at": scan.created_at.isoformat() if scan.created_at else None,
                        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None
                    }
                    yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            db.close()
        
        await asyncio.sleep(2)


@router.get("/api/scans/live")
async def live_scans(repo_id: Optional[int] = None):
    """
    SSE endpoint for real-time scan updates.
    Frontend connects with: new EventSource('/api/scans/live')
    """
    return StreamingResponse(
        scan_event_generator(repo_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Important for nginx proxying
            "Connection": "keep-alive"
        }
    )


@router.get("/api/scans")
async def list_scans(repo_id: Optional[int] = None, limit: int = 20):
    """
    Get list of recent scans (non-SSE, for initial page load).
    """
    db = SessionLocal()
    try:
        query = db.query(Scan).order_by(Scan.created_at.desc()).limit(limit)
        if repo_id:
            query = query.filter(Scan.repo_id == repo_id)
        scans = query.all()
        return [
            {
                "id": s.id,
                "repo_id": s.repo_id,
                "commit_sha": s.commit_sha,
                "branch": s.branch,
                "status": s.status,
                "vulnerability_type": s.vulnerability_type,
                "severity": s.severity,
                "vulnerable_file": s.vulnerable_file,
                "exploit_output": s.exploit_output,
                "patch_diff": s.patch_diff,
                "pr_url": s.pr_url,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None
            }
            for s in scans
        ]
    finally:
        db.close()


@router.get("/api/scans/{scan_id}")
async def get_scan(scan_id: int):
    """
    Get details of a specific scan.
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return {"error": "Scan not found"}, 404
        
        return {
            "id": scan.id,
            "repo_id": scan.repo_id,
            "commit_sha": scan.commit_sha,
            "branch": scan.branch,
            "status": scan.status,
            "vulnerability_type": scan.vulnerability_type,
            "severity": scan.severity,
            "vulnerable_file": scan.vulnerable_file,
            "exploit_output": scan.exploit_output,
            "patch_diff": scan.patch_diff,
            "pr_url": scan.pr_url,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None
        }
    finally:
        db.close()

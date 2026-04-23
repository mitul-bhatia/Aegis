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
    Polls DB every 1 second and emits scans that have changed or are new.
    """
    seen_scans = {}  # scan_id -> (status, updated_at)
    
    # Send initial heartbeat
    yield f": heartbeat\n\n"
    
    while True:
        db = SessionLocal()
        try:
            query = db.query(Scan).order_by(Scan.created_at.desc()).limit(50)
            if repo_id:
                query = query.filter(Scan.repo_id == repo_id)
            scans = query.all()
            
            for scan in scans:
                scan_key = (scan.status, str(scan.created_at))
                
                # Emit if it's a new scan or status changed
                if scan.id not in seen_scans or seen_scans.get(scan.id) != scan_key:
                    seen_scans[scan.id] = scan_key
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
                    logger.info(f"SSE: Emitting scan {scan.id} with status {scan.status}")
                    yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            db.close()
        
        # Poll every 1 second for faster updates
        await asyncio.sleep(1)


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


@router.post("/api/scans/trigger")
async def trigger_manual_scan(repo_id: int):
    """
    Manually trigger a scan on a repository's latest commit.
    Useful for testing without webhooks.
    """
    from orchestrator import run_aegis_pipeline
    from database.models import Repo
    import requests
    
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            return {"error": "Repository not found"}, 404
        
        # Get latest commit from GitHub
        import config
        api_url = f"https://api.github.com/repos/{repo.full_name}/commits/main"
        headers = {}
        if config.GITHUB_TOKEN:
            headers["Authorization"] = f"token {config.GITHUB_TOKEN}"
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return {"error": f"Failed to fetch commit: {response.status_code}", "details": response.text}, 500
        
        commit_data = response.json()
        commit_sha = commit_data["sha"]
        files_changed = [f["filename"] for f in commit_data["files"]]
        
        # Create push info
        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": "main",
            "files_changed": files_changed,
            "is_pr": False,
        }
        
        logger.info(f"Manual scan triggered for {repo.full_name} @ {commit_sha[:8]}")
        
        # Run pipeline in background with error handling
        import threading
        import traceback
        
        def run_with_error_handling():
            try:
                logger.info(f"Starting pipeline thread for {repo.full_name}")
                run_aegis_pipeline(push_info)
                logger.info(f"Pipeline thread completed for {repo.full_name}")
            except Exception as e:
                logger.error(f"Pipeline thread error: {e}")
                logger.error(traceback.format_exc())
        
        thread = threading.Thread(target=run_with_error_handling)
        thread.daemon = True
        thread.start()
        logger.info(f"Pipeline thread started (thread ID: {thread.ident})")
        
        return {
            "message": "Scan triggered successfully",
            "repo": repo.full_name,
            "commit": commit_sha[:8],
            "files": files_changed
        }
    finally:
        db.close()

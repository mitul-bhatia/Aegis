"""
SSE (Server-Sent Events) endpoint for real-time scan updates
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus
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
    seen_scans = {}  # scan_id -> status
    
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
                scan_key = (scan.status, scan.agent_message, str(scan.created_at))
                
                # Emit if it's a new scan or status/agent changed
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
                        "current_agent": scan.current_agent,
                        "agent_message": scan.agent_message,
                        "exploit_output": scan.exploit_output,
                        "patch_diff": scan.patch_diff,
                        "pr_url": scan.pr_url,
                        "created_at": scan.created_at.isoformat() if scan.created_at else None,
                        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None
                    }
                    logger.info(f"SSE: Emitting scan {scan.id} status={scan.status} agent={scan.current_agent}")
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


def _scan_to_dict(s: Scan) -> dict:
    """Convert a Scan ORM object to the full API response dict."""
    return {
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
        "error_message": s.error_message,
        # Agent-identity fields (new)
        "original_code": s.original_code,
        "exploit_script": s.exploit_script,
        "findings_json": s.findings_json,
        "current_agent": s.current_agent,
        "agent_message": s.agent_message,
        "patch_attempts": s.patch_attempts,
        # Timing
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None
    }


@router.get("/api/scans")
async def list_scans(repo_id: Optional[int] = None, limit: int = 20):
    """
    Get list of recent scans (non-SSE, for initial page load).
    """
    db = SessionLocal()
    try:
        query = db.query(Scan).order_by(Scan.created_at.desc())
        if repo_id:
            query = query.filter(Scan.repo_id == repo_id)
        scans = query.limit(limit).all()
        return [_scan_to_dict(s) for s in scans]
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
        return _scan_to_dict(scan)
    finally:
        db.close()


@router.post("/api/scans/trigger")
async def trigger_manual_scan(repo_id: int):
    """Manually trigger a scan on a repository's latest commit."""
    from orchestrator import run_aegis_pipeline
    from fastapi import HTTPException
    import threading, traceback

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Get latest commit — run in thread to avoid blocking event loop
        def _fetch():
            from github import Github
            g = Github(config.GITHUB_TOKEN)
            gr = g.get_repo(repo.full_name)
            branch = gr.default_branch
            sha = gr.get_branch(branch).commit.sha
            files = [f.filename for f in gr.get_commit(sha).files]
            return branch, sha, files

        import concurrent.futures, asyncio
        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                default_branch, commit_sha, files_changed = await asyncio.wait_for(
                    loop.run_in_executor(ex, _fetch), timeout=15
                )
        except (asyncio.TimeoutError, Exception) as gh_err:
            logger.error(f"GitHub API error: {gh_err}")
            return {"error": "Failed to fetch commit", "details": str(gh_err)}, 500

        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": default_branch,
            "files_changed": files_changed,
            "is_pr": False,
        }

        logger.info(f"Manual scan triggered for {repo.full_name} @ {commit_sha[:8]}")

        def _run():
            try:
                logger.info(f"Starting pipeline thread for {repo.full_name}")
                run_aegis_pipeline(push_info)
                logger.info(f"Pipeline thread completed for {repo.full_name}")
            except Exception as e:
                logger.error(f"Pipeline thread error: {e}\n{traceback.format_exc()}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        logger.info(f"Pipeline thread started (thread ID: {t.ident})")

        return {"message": "Scan triggered successfully", "repo": repo.full_name,
                "commit": commit_sha[:8], "files": files_changed}
    finally:
        db.close()


@router.post("/api/scans/trigger-direct")
async def trigger_direct_scan(repo_id: int, commit_sha: str, branch: str = "main"):
    """Trigger a scan directly with a known commit SHA — no GitHub API call needed."""
    from orchestrator import run_aegis_pipeline
    from fastapi import HTTPException
    import threading, traceback

    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": branch,
            "files_changed": ["app.py"],
            "is_pr": False,
        }

        logger.info(f"Direct scan triggered for {repo.full_name} @ {commit_sha[:8]}")

        def _run():
            try:
                run_aegis_pipeline(push_info)
                logger.info(f"Pipeline completed for {repo.full_name}")
            except Exception as e:
                logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")

        threading.Thread(target=_run, daemon=True).start()
        return {"message": "Scan triggered", "repo": repo.full_name, "commit": commit_sha[:8]}
    finally:
        db.close()


@router.get("/api/stats")
async def get_stats(user_id: int):
    """
    Aggregate stats for dashboard stat cards.
    Returns total repos, active scans, vulns fixed, etc.
    """
    db = SessionLocal()
    try:
        # Get user's repos
        repos = db.query(Repo).filter(Repo.user_id == user_id).all()
        repo_ids = [r.id for r in repos]

        if not repo_ids:
            return {
                "total_repos": 0,
                "active_scans": 0,
                "vulns_fixed": 0,
                "total_scans": 0,
                "false_positives": 0,
                "last_scan_at": None
            }

        active_statuses = [
            ScanStatus.QUEUED.value,
            ScanStatus.SCANNING.value,
            ScanStatus.EXPLOITING.value,
            ScanStatus.EXPLOIT_CONFIRMED.value,
            ScanStatus.PATCHING.value,
            ScanStatus.VERIFYING.value,
        ]

        total_scans = db.query(Scan).filter(Scan.repo_id.in_(repo_ids)).count()

        active_scans = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids),
            Scan.status.in_(active_statuses)
        ).count()

        vulns_fixed = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids),
            Scan.status == ScanStatus.FIXED.value
        ).count()

        false_positives = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids),
            Scan.status == ScanStatus.FALSE_POSITIVE.value
        ).count()

        last_scan = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids)
        ).order_by(Scan.created_at.desc()).first()

        return {
            "total_repos": len(repos),
            "active_scans": active_scans,
            "vulns_fixed": vulns_fixed,
            "total_scans": total_scans,
            "false_positives": false_positives,
            "last_scan_at": last_scan.created_at.isoformat() if last_scan else None
        }
    finally:
        db.close()

"""
Aegis — Scan Routes + SSE Live Feed

Two types of endpoints here:
1. Regular REST endpoints (list scans, get scan, trigger scan, stats)
2. SSE endpoint (/api/scans/live) — pushes real-time updates to the browser

HOW SSE WORKS (old vs new):
  OLD: Every connected browser tab polled the DB every 1 second.
       20 users = 1,200 DB reads/minute just for the live feed.

  NEW: The orchestrator calls notify_scan_update_sync() after every status change.
       That pushes the update into the event_bus (in-memory queue).
       Each SSE client just waits on its own queue — zero DB reads.
       Updates are instant instead of up to 1 second delayed.
"""

import asyncio
import json
import logging
import threading
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

import config
from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus
from utils.event_bus import event_bus
from utils.limiter import limiter
from github_integration.pr_creator import create_pull_request

router = APIRouter()
logger = logging.getLogger(__name__)


# ── SSE Bridge: sync → async ──────────────────────────────
# The orchestrator runs in a background thread (not async).
# asyncio queues can only be written from the event loop thread.
# So we grab the running event loop and schedule the publish from there.

# Stored at startup so the sync bridge can reach it
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    """Called once at app startup to store the running event loop."""
    global _event_loop
    _event_loop = loop


def notify_scan_update_sync(scan_data: dict):
    """
    Called by orchestrator (sync thread) after every DB status change.
    Schedules an async publish on the main event loop so all SSE clients
    receive the update instantly — no DB polling needed.
    """
    if _event_loop is None or _event_loop.is_closed():
        return  # App not fully started yet, skip

    # thread-safe way to schedule a coroutine on the async event loop
    asyncio.run_coroutine_threadsafe(event_bus.publish(scan_data), _event_loop)


# ── SSE Generator ─────────────────────────────────────────

async def scan_event_generator(repo_id: Optional[int] = None):
    """
    Async generator that yields SSE events to one browser tab.

    - Subscribes to the event bus (gets its own queue)
    - Waits for updates — no DB reads at all
    - Sends a keepalive comment every 30s to prevent connection timeout
    - Cleans up its queue when the client disconnects
    """
    # Each connected client gets its own queue
    queue = event_bus.subscribe()

    # Send an initial heartbeat so the browser knows the connection is open
    yield ": heartbeat\n\n"

    try:
        while True:
            try:
                # Wait up to 30 seconds for an update
                scan_data = await asyncio.wait_for(queue.get(), timeout=30)

                # If this SSE stream is filtered to one repo, skip other repos
                if repo_id is not None and scan_data.get("repo_id") != repo_id:
                    continue

                logger.debug(
                    f"SSE: pushing scan {scan_data.get('id')} "
                    f"status={scan_data.get('status')}"
                )
                yield f"data: {json.dumps(scan_data)}\n\n"

            except asyncio.TimeoutError:
                # No update in 30s — send a keepalive so the connection stays open
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        # Client disconnected — clean up
        pass
    finally:
        event_bus.unsubscribe(queue)
        logger.debug("SSE client disconnected — queue removed")


# ── SSE Endpoint ──────────────────────────────────────────

@router.get("/api/v1/scans/live")
async def live_scans(repo_id: Optional[int] = None):
    """
    SSE endpoint — browser connects once and receives all scan updates in real time.
    Usage: new EventSource('/api/scans/live')
    """
    return StreamingResponse(
        scan_event_generator(repo_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # tells nginx not to buffer SSE
            "Connection": "keep-alive",
        },
    )


# ── Helpers ───────────────────────────────────────────────

def _scan_to_dict(s: Scan) -> dict:
    """Convert a Scan ORM object to a JSON-serializable dict."""
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
        "original_code": s.original_code,
        "exploit_script": s.exploit_script,
        "findings_json": s.findings_json,
        "current_agent": s.current_agent,
        "agent_message": s.agent_message,
        "patch_attempts": s.patch_attempts,
        "is_regression": getattr(s, "is_regression", False),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


# ── REST Endpoints ────────────────────────────────────────

@router.get("/api/v1/scans")
async def list_scans(
    repo_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
):
    """
    List scans with pagination.
    - page: which page to return (starts at 1)
    - per_page: how many items per page (max 100)
    - repo_id: filter to a specific repo
    - status: filter by scan status (e.g. 'fixed', 'failed')

    Returns: { data: [...], pagination: { page, per_page, total, total_pages } }
    """
    import math

    # Clamp per_page between 1 and 100
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page

    db = SessionLocal()
    try:
        query = db.query(Scan).order_by(Scan.created_at.desc())

        if repo_id:
            query = query.filter(Scan.repo_id == repo_id)
        if status:
            query = query.filter(Scan.status == status)

        total = query.count()
        scans = query.offset(offset).limit(per_page).all()

        return {
            "data": [_scan_to_dict(s) for s in scans],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": math.ceil(total / per_page) if total > 0 else 1,
            },
        }
    finally:
        db.close()


@router.get("/api/v1/scans/{scan_id}")
async def get_scan(scan_id: int):
    """Get full details of a single scan by ID."""
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        return _scan_to_dict(scan)
    finally:
        db.close()


@router.post("/api/v1/scans/trigger")
@limiter.limit("5/minute")    # each scan spins up Docker + LLM calls — expensive
async def trigger_manual_scan(request: Request, repo_id: int):
    """
    Manually trigger a scan on a repo's latest commit.
    Fetches the latest commit SHA from GitHub, then runs the pipeline.
    """
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Fetch latest commit from GitHub in a thread (blocking I/O)
        def _fetch_latest_commit():
            from github import Github
            g = Github(config.GITHUB_TOKEN)
            gr = g.get_repo(repo.full_name)
            branch = gr.default_branch
            sha = gr.get_branch(branch).commit.sha
            files = [f.filename for f in gr.get_commit(sha).files]
            return branch, sha, files

        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                default_branch, commit_sha, files_changed = await asyncio.wait_for(
                    loop.run_in_executor(ex, _fetch_latest_commit), timeout=15
                )
        except Exception as gh_err:
            logger.error(f"GitHub API error: {gh_err}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch commit: {gh_err}")

        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": default_branch,
            "files_changed": files_changed,
            "is_pr": False,
        }

        # Run pipeline in a background thread so we return immediately
        def _run_pipeline():
            try:
                from orchestrator import run_aegis_pipeline
                run_aegis_pipeline(push_info)
            except Exception as e:
                logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")

        threading.Thread(target=_run_pipeline, daemon=True).start()
        logger.info(f"Manual scan triggered: {repo.full_name} @ {commit_sha[:8]}")

        return {
            "message": "Scan triggered successfully",
            "repo": repo.full_name,
            "commit": commit_sha[:8],
            "files": files_changed,
        }
    finally:
        db.close()


@router.post("/api/v1/scans/trigger-direct")
@limiter.limit("5/minute")    # same cost as trigger — cap at 5 per minute per IP
async def trigger_direct_scan(request: Request, repo_id: int, commit_sha: str, branch: str = "main"):
    """
    Trigger a scan with a known commit SHA — skips the GitHub API call.
    Used by the frontend's 'Scan' button which already knows the last commit.
    """
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        def _fetch_files_changed():
            from github import Github
            g = Github(config.GITHUB_TOKEN)
            gr = g.get_repo(repo.full_name)
            files = [f.filename for f in gr.get_commit(commit_sha).files]
            return files

        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                files_changed = await asyncio.wait_for(
                    loop.run_in_executor(ex, _fetch_files_changed), timeout=15
                )
        except Exception as gh_err:
            logger.error(f"GitHub API error fetching files: {gh_err}")
            files_changed = ["app.py"]

        push_info = {
            "repo_name": repo.full_name,
            "repo_url": f"https://github.com/{repo.full_name}.git",
            "commit_sha": commit_sha,
            "branch": branch,
            "files_changed": files_changed,
            "is_pr": False,
        }

        def _run_pipeline():
            try:
                from orchestrator import run_aegis_pipeline
                run_aegis_pipeline(push_info)
            except Exception as e:
                logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")

        threading.Thread(target=_run_pipeline, daemon=True).start()
        logger.info(f"Direct scan triggered: {repo.full_name} @ {commit_sha[:8]}")

        return {
            "message": "Scan triggered",
            "repo": repo.full_name,
            "commit": commit_sha[:8],
        }
    finally:
        db.close()


@router.get("/api/v1/stats")
async def get_stats(user_id: int):
    """
    Dashboard stat cards — total repos, active scans, vulns fixed, etc.
    """
    db = SessionLocal()
    try:
        repos = db.query(Repo).filter(Repo.user_id == user_id).all()
        repo_ids = [r.id for r in repos]

        if not repo_ids:
            return {
                "total_repos": 0,
                "active_scans": 0,
                "vulns_fixed": 0,
                "total_scans": 0,
                "false_positives": 0,
                "last_scan_at": None,
            }

        # Statuses that mean a scan is currently running
        active_statuses = [
            ScanStatus.QUEUED.value,
            ScanStatus.SCANNING.value,
            ScanStatus.EXPLOITING.value,
            ScanStatus.EXPLOIT_CONFIRMED.value,
            ScanStatus.PATCHING.value,
            ScanStatus.VERIFYING.value,
            ScanStatus.AWAITING_APPROVAL.value,  # Include awaiting approval as active
        ]

        total_scans = db.query(Scan).filter(Scan.repo_id.in_(repo_ids)).count()
        active_scans = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids), Scan.status.in_(active_statuses)
        ).count()
        vulns_fixed = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids), Scan.status == ScanStatus.FIXED.value
        ).count()
        false_positives = db.query(Scan).filter(
            Scan.repo_id.in_(repo_ids), Scan.status == ScanStatus.FALSE_POSITIVE.value
        ).count()
        last_scan = (
            db.query(Scan)
            .filter(Scan.repo_id.in_(repo_ids))
            .order_by(Scan.created_at.desc())
            .first()
        )

        return {
            "total_repos": len(repos),
            "active_scans": active_scans,
            "vulns_fixed": vulns_fixed,
            "total_scans": total_scans,
            "false_positives": false_positives,
            "last_scan_at": last_scan.created_at.isoformat() if last_scan else None,
        }
    finally:
        db.close()


# ── Human-in-the-Loop Approval ────────────────────────────

@router.post("/api/v1/scans/{scan_id}/approve")
async def approve_critical_fix(scan_id: int):
    """
    Approve a CRITICAL vulnerability fix and resume the pipeline to create the PR.
    This endpoint is called when a human reviews and approves the patch.
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if scan.status != ScanStatus.AWAITING_APPROVAL.value:
            raise HTTPException(
                status_code=400,
                detail=f"Scan is not awaiting approval (current status: {scan.status})"
            )
        
        # Update status to verifying while PR is being created
        scan.status = ScanStatus.VERIFYING.value
        scan.agent_message = "Human approved patch — creating PR..."
        db.commit()
        
        # Broadcast the update via SSE
        notify_scan_update_sync(_scan_to_dict(scan))
        
        # Trigger PR creation in background
        def _create_pr():
            # Open a fresh DB session for the background thread
            _db = SessionLocal()
            try:
                _scan = _db.query(Scan).filter(Scan.id == scan_id).first()
                if not _scan:
                    return

                repo = _db.query(Repo).filter(Repo.id == _scan.repo_id).first()
                if not repo:
                    raise Exception("Repository not found")

                pr_url = create_pull_request(
                    repo_full_name=repo.full_name,
                    base_branch=_scan.branch,
                    file_path=_scan.vulnerable_file,
                    patched_code=_scan.patch_diff,
                    vulnerability_type=_scan.vulnerability_type,
                    exploit_output=_scan.exploit_output,
                )

                _scan.status = ScanStatus.FIXED.value
                _scan.pr_url = pr_url
                _scan.agent_message = f"Fixed: {_scan.vulnerability_type}. PR: {pr_url}"
                _scan.current_agent = None
                _db.commit()

                notify_scan_update_sync(_scan_to_dict(_scan))
                logger.info(f"PR created after approval: {pr_url}")

            except Exception as e:
                logger.error(f"PR creation failed after approval: {e}\n{traceback.format_exc()}")
                try:
                    _scan = _db.query(Scan).filter(Scan.id == scan_id).first()
                    if _scan:
                        _scan.status = ScanStatus.FAILED.value
                        _scan.error_message = f"PR creation failed: {str(e)}"
                        _db.commit()
                        notify_scan_update_sync(_scan_to_dict(_scan))
                except Exception:
                    pass
            finally:
                _db.close()
        
        threading.Thread(target=_create_pr, daemon=True).start()
        
        logger.info(f"Scan #{scan_id} approved — creating PR")
        return {"message": "Patch approved — creating PR", "scan_id": scan_id}
        
    finally:
        db.close()


@router.post("/api/v1/scans/{scan_id}/reject")
async def reject_fix(scan_id: int, reason: str = ""):
    """
    Reject a CRITICAL vulnerability fix.
    Marks the scan as failed with the rejection reason.
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if scan.status != ScanStatus.AWAITING_APPROVAL.value:
            raise HTTPException(
                status_code=400,
                detail=f"Scan is not awaiting approval (current status: {scan.status})"
            )
        
        # Mark as failed with rejection reason
        scan.status = ScanStatus.FAILED.value
        scan.error_message = f"Patch rejected by human reviewer: {reason}" if reason else "Patch rejected by human reviewer"
        db.commit()
        
        # Broadcast the update via SSE
        notify_scan_update_sync(_scan_to_dict(scan))
        
        logger.info(f"Scan #{scan_id} rejected: {reason}")
        return {"message": "Patch rejected", "scan_id": scan_id}
        
    finally:
        db.close()

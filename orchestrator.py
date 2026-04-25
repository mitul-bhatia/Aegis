"""
Aegis Orchestrator

This is the entry point called by main.py when a webhook fires.
It sets up the initial pipeline state and hands off to the
LangGraph state machine in pipeline/graph.py.

All the actual pipeline logic lives in:
  pipeline/nodes.py  — what each step does
  pipeline/graph.py  — how steps connect and route
  pipeline/state.py  — the shared data structure

We keep the DB helpers (update_scan_status, _create_scan, etc.) here
because they are imported by pipeline/nodes.py and routes/scans.py.
"""

import logging
from datetime import datetime, timezone

import config
from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus
from utils.logging import get_logger

logger = logging.getLogger(__name__)
# Structured logger — used for pipeline logs that need scan_id/repo/commit context
slog = get_logger(__name__)


# ── DB Status Update Helper ───────────────────────────────
# Called by pipeline nodes to write real-time status to DB and broadcast SSE.

def update_scan_status(scan_id: int, status: str, extra: dict = None):
    """
    Write the current pipeline status to the scans table and broadcast
    the update over SSE so the frontend updates in real time.

    Args:
        scan_id : DB scan record ID
        status  : new ScanStatus value (e.g. "scanning", "patching")
        extra   : optional dict of additional fields to update on the scan row
    """
    if not scan_id:
        return

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return

        scan.status = status

        terminal_statuses = {
            ScanStatus.FIXED.value,
            ScanStatus.CLEAN.value,
            ScanStatus.FAILED.value,
            ScanStatus.FALSE_POSITIVE.value,
        }
        if status in terminal_statuses and not scan.completed_at:
            scan.completed_at = datetime.now(timezone.utc)

        if extra:
            # Map each allowed field from extra onto the scan row
            allowed_fields = {
                "vulnerability_type", "severity", "vulnerable_file",
                "exploit_output", "patch_diff", "pr_url",
                "current_agent", "agent_message", "original_code",
                "exploit_script", "findings_json", "patch_attempts",
                "error_message",
            }
            for field in allowed_fields:
                if field in extra:
                    setattr(scan, field, extra[field])

        db.commit()
        db.refresh(scan)
        _broadcast(scan)
        _maybe_notify(scan)
        logger.debug(f"[DB] Scan {scan_id} → {status}")

    except Exception as e:
        logger.warning(f"[DB] Status update failed: {e}")
    finally:
        db.close()


# ── DB Helpers ────────────────────────────────────────────

def _get_repo_id(db, repo_full_name: str):
    """Look up a repo by full_name. Returns None if not found."""
    repo = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
    return repo.id if repo else None


def _create_scan(db, repo_id: int, commit_sha: str, branch: str) -> Scan:
    """
    Create a new scan record, or return the existing one if this commit
    was already scanned (prevents duplicate runs from webhook retries).
    """
    existing = db.query(Scan).filter(
        Scan.repo_id == repo_id,
        Scan.commit_sha == commit_sha,
    ).first()

    if existing:
        logger.info(
            f"Duplicate scan for {commit_sha[:8]} "
            f"(scan #{existing.id}, status={existing.status}) — skipping."
        )
        return existing

    scan = Scan(
        repo_id=repo_id,
        commit_sha=commit_sha,
        branch=branch,
        status=ScanStatus.QUEUED.value,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def _broadcast(scan: Scan):
    """Fire-and-forget SSE broadcast of the current scan state."""
    try:
        from routes.scans import notify_scan_update_sync
        notify_scan_update_sync({
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
            "exploit_script": scan.exploit_script,
            "original_code": scan.original_code,
            "findings_json": scan.findings_json,
            "patch_diff": scan.patch_diff,
            "patch_attempts": scan.patch_attempts,
            "pr_url": scan.pr_url,
            "error_message": scan.error_message,
            "created_at": str(scan.created_at),
            "completed_at": str(scan.completed_at) if scan.completed_at else None,
        })
    except Exception:
        pass  # SSE is non-critical — never crash the pipeline over it


def _maybe_notify(scan: Scan):
    """
    Fire Slack/Discord notifications for notable scan status changes.
    Only triggers for states worth alerting on — silently skips the rest.
    """
    notable = {
        ScanStatus.FIXED.value,
        ScanStatus.FAILED.value,
        ScanStatus.EXPLOIT_CONFIRMED.value,
        ScanStatus.AWAITING_APPROVAL.value,
        ScanStatus.FALSE_POSITIVE.value,
    }
    if scan.status not in notable:
        return

    try:
        from notifications.notifier import notify_scan_event, ScanEvent

        # Build the deep-link URL to the scan detail page
        scan_url = f"{config.FRONTEND_URL}/scans/{scan.id}"

        # Get repo name safely
        repo_name = "unknown"
        try:
            repo_name = scan.repo.full_name
        except Exception:
            pass

        event = ScanEvent(
            scan_id=scan.id,
            repo_name=repo_name,
            status=scan.status,
            vulnerability_type=scan.vulnerability_type,
            severity=scan.severity,
            vulnerable_file=scan.vulnerable_file,
            pr_url=scan.pr_url,
            error_message=scan.error_message,
            scan_url=scan_url,
        )
        notify_scan_event(event)
    except Exception as e:
        logger.debug(f"Notification skipped: {e}")


# ── Main Pipeline Entry Point ─────────────────────────────

def run_aegis_pipeline(push_info: dict):
    """
    Entry point called by main.py when a GitHub webhook fires.

    1. Creates a DB scan record (or finds the existing one for this commit).
    2. Builds the initial LangGraph state.
    3. Runs the compiled pipeline graph.
    4. Logs the final result.

    All the actual work happens inside pipeline/nodes.py.
    """
    repo_full_name = push_info["repo_name"]
    commit_sha     = push_info["commit_sha"]
    branch         = push_info.get("branch", "main")

    # Bind scan context — every log below carries repo + commit automatically
    pipeline_log = slog.bind(repo=repo_full_name, commit=commit_sha[:8], branch=branch)
    pipeline_log.info("pipeline.started")

    db = SessionLocal()
    scan = None

    try:
        # Create (or find existing) scan record
        repo_id = _get_repo_id(db, repo_full_name)
        if repo_id:
            scan = _create_scan(db, repo_id, commit_sha, branch)

            # If already completed, this is a duplicate webhook — skip
            terminal_statuses = {
                ScanStatus.FIXED.value,
                ScanStatus.CLEAN.value,
                ScanStatus.FAILED.value,
                ScanStatus.FALSE_POSITIVE.value,
            }
            if scan.status in terminal_statuses:
                pipeline_log.info(
                    "pipeline.skipped",
                    scan_id=scan.id,
                    reason="duplicate_webhook",
                    status=scan.status,
                )
                return

        # Once we have a scan ID, rebind the logger with it
        if scan:
            pipeline_log = pipeline_log.bind(scan_id=scan.id)

        # Build the initial state for the LangGraph pipeline
        initial_state = {
            "repo_full_name": repo_full_name,
            "commit_sha": commit_sha,
            "branch": branch,
            "push_info": push_info,
            "scan_id": scan.id if scan else None,
            # These will be populated by the nodes:
            "local_repo_path": "",
            "diff": {},
            "semgrep_findings": [],
            "rag_context": "",
            "dependency_vulns": [],
            "vulnerability_findings": [],
            "confirmed_vulnerabilities": [],
            "current_vuln_index": 0,
            "patched_code": None,
            "test_code": None,
            "original_code": None,
            "verification_passed": False,
            "awaiting_approval": False,
            "retry_count": 0,
            "max_retries": config.MAX_PATCH_RETRIES,
            "pr_urls": [],
            # Shared Artifact Store
            "exploit_artifacts": [],
            "patch_artifacts": [],
            "safety_report": None,
            # Post-patch re-scan control
            "rescan_needed": False,
            "rescan_count": 0,
            "pipeline_status": "queued",
            "error": None,
        }

        # Run the LangGraph pipeline
        from pipeline.graph import aegis_pipeline
        result = aegis_pipeline.invoke(initial_state)

        # Log the final outcome
        pr_urls = result.get("pr_urls", [])
        status  = result.get("pipeline_status", "unknown")
        error   = result.get("error")

        if error:
            pipeline_log.error("pipeline.error", error=error)
        elif pr_urls:
            pipeline_log.info("pipeline.complete", prs_opened=len(pr_urls), pr_urls=pr_urls)
        else:
            pipeline_log.info("pipeline.complete", status=status)

    except Exception as e:
        pipeline_log.exception("pipeline.crashed", error=str(e))
        if scan:
            try:
                update_scan_status(
                    scan.id,
                    ScanStatus.FAILED.value,
                    {"error_message": str(e)},
                )
            except Exception:
                pass
    finally:
        db.close()

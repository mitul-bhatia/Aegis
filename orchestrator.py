import os
import logging
import asyncio
from datetime import datetime, timezone

import config

from github_integration.diff_fetcher import clone_or_pull_repo, get_diff
from scanner.semgrep_runner import run_semgrep_on_files
from rag.retriever import retrieve_relevant_context
from agents.hacker import run_hacker_agent
from sandbox.docker_runner import run_exploit_in_sandbox
from agents.reviewer import run_remediation_loop
from github_integration.pr_creator import create_pull_request
from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus

logger = logging.getLogger(__name__)


# ── DB + SSE helpers ──────────────────────────────────────

def _get_repo_id(db, repo_full_name: str):
    """Lookup repo in DB by full_name. Returns None if not found."""
    repo = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
    return repo.id if repo else None


def _create_scan(db, repo_id, commit_sha: str, branch: str) -> Scan:
    """Create a scan record and return it."""
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


def _update_scan(db, scan: Scan, **kwargs):
    """Update scan fields and broadcast SSE notification."""
    for key, value in kwargs.items():
        setattr(scan, key, value)
    db.commit()
    db.refresh(scan)
    _broadcast(scan)


def _complete_scan(db, scan: Scan, **kwargs):
    """Mark scan as complete with a timestamp."""
    kwargs["completed_at"] = datetime.now(timezone.utc)
    _update_scan(db, scan, **kwargs)


def _broadcast(scan: Scan):
    """Fire-and-forget SSE broadcast of current scan state."""
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
            "pr_url": scan.pr_url,
            "created_at": str(scan.created_at),
        })
    except Exception:
        pass  # SSE is non-critical


# ── Main Pipeline ─────────────────────────────────────────

def run_aegis_pipeline(push_info: dict):
    """
    The main Aegis pipeline. Runs in background after a webhook fires.
    Now writes every status change to the database and broadcasts over SSE.
    """
    repo_full_name = push_info["repo_name"]
    commit_sha = push_info["commit_sha"]
    branch = push_info.get("branch", "main")

    logger.info(f"=== Aegis Pipeline: {repo_full_name} @ {commit_sha[:8]} ===")

    db = SessionLocal()
    scan = None

    try:
        # Look up repo in DB (may not exist if webhook was manually installed)
        repo_id = _get_repo_id(db, repo_full_name)
        if repo_id:
            scan = _create_scan(db, repo_id, commit_sha, branch)

        # ── Phase 2: Clone + Diff + Semgrep ──────────────
        if scan:
            _update_scan(db, scan, status=ScanStatus.SCANNING.value)

        local_repo_path = os.path.join(
            config.REPOS_DIR, repo_full_name.replace("/", "_")
        )

        # Use user token if available
        repo_obj = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
        if repo_obj and repo_obj.user:
            clone_url = f"https://x-access-token:{repo_obj.user.github_token}@github.com/{repo_full_name}.git"
        else:
            clone_url = push_info.get("repo_url", f"https://github.com/{repo_full_name}.git")

        clone_or_pull_repo(clone_url, local_repo_path)
        diff = get_diff(repo_full_name, commit_sha)

        if not diff["changed_files"]:
            logger.info("No supported code files changed. Pipeline done.")
            if scan:
                _complete_scan(db, scan, status=ScanStatus.CLEAN.value)
            return

        file_paths = [f["filename"] for f in diff["changed_files"]]
        semgrep_findings = run_semgrep_on_files(file_paths, local_repo_path)

        if not semgrep_findings:
            logger.info("✅ Semgrep clean — no issues found.")
            if scan:
                _complete_scan(db, scan, status=ScanStatus.CLEAN.value)
            return

        logger.warning(f"⚠️  Semgrep: {len(semgrep_findings)} issue(s) → escalating to Agent A")

        # Record initial vuln info from Semgrep
        first_finding = semgrep_findings[0]
        if scan:
            _update_scan(
                db, scan,
                vulnerability_type=first_finding.get("category", "Security Issue"),
                severity=first_finding.get("severity", "WARNING"),
                vulnerable_file=first_finding.get("file", ""),
            )

        # ── Phase 3: RAG Context ──────────────────────────
        rag_context = retrieve_relevant_context(repo_full_name, diff, semgrep_findings)

        # ── Phase 4: Agent A (Hacker) ─────────────────────
        if scan:
            _update_scan(db, scan, status=ScanStatus.EXPLOITING.value)

        hacker_result = run_hacker_agent(diff, semgrep_findings, rag_context)
        exploit_script = hacker_result["exploit_script"]
        vulnerability_type = hacker_result["vulnerability_type"]

        if scan:
            _update_scan(
                db, scan,
                vulnerability_type=vulnerability_type,
            )

        # ── Phase 5: Sandbox Exploit Test ─────────────────
        exploit_test = run_exploit_in_sandbox(exploit_script, local_repo_path)

        if not exploit_test["exploit_succeeded"]:
            logger.info("✅ Exploit failed — likely a false positive.")
            if scan:
                _complete_scan(
                    db, scan,
                    status=ScanStatus.FALSE_POSITIVE.value,
                    exploit_output=exploit_test["stdout"],
                )
            return

        logger.error(f"🚨 VULNERABILITY CONFIRMED: {vulnerability_type}")

        if scan:
            _update_scan(
                db, scan,
                status=ScanStatus.EXPLOIT_CONFIRMED.value,
                exploit_output=exploit_test["stdout"],
            )

        # ── Phase 6+7: Engineer + Reviewer Loop ──────────
        if scan:
            _update_scan(db, scan, status=ScanStatus.PATCHING.value)

        vulnerable_file = semgrep_findings[0]["file"]
        full_vulnerable_path = os.path.join(local_repo_path, vulnerable_file)

        with open(full_vulnerable_path, "r") as f:
            original_code = f.read()

        remediation = run_remediation_loop(
            vulnerable_code=original_code,
            file_path=vulnerable_file,
            exploit_script=exploit_script,
            exploit_output=exploit_test["stdout"],
            vulnerability_type=vulnerability_type,
            repo_path=local_repo_path,
        )

        if not remediation["success"]:
            logger.error("❌ Remediation failed — human review required.")
            if scan:
                _complete_scan(
                    db, scan,
                    status=ScanStatus.FAILED.value,
                    error_message="Agent could not generate a working patch after max retries.",
                )
            return

        # ── Phase 8: Open PR ──────────────────────────────
        if scan:
            _update_scan(db, scan, status=ScanStatus.VERIFYING.value)

        logger.info("🚀 Opening PR with fix and exploit proof...")
        pr_url = create_pull_request(
            repo_full_name=repo_full_name,
            base_branch=branch,
            file_path=vulnerable_file,
            patched_code=remediation["patched_code"],
            vulnerability_type=vulnerability_type,
            exploit_output=exploit_test["stdout"],
        )

        if scan:
            _complete_scan(
                db, scan,
                status=ScanStatus.FIXED.value,
                patch_diff=remediation["patched_code"],
                pr_url=pr_url,
            )

        logger.info(f"🎉 Done! PR: {pr_url}")

    except Exception as e:
        logger.exception(f"Pipeline crashed: {e}")
        if scan and db:
            try:
                _complete_scan(
                    db, scan,
                    status=ScanStatus.FAILED.value,
                    error_message=str(e),
                )
            except Exception:
                pass
    finally:
        db.close()

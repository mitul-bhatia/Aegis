import os
import logging
import asyncio
from datetime import datetime, timezone

import config

from github_integration.diff_fetcher import clone_or_pull_repo, get_diff
from scanner.semgrep_runner import run_semgrep_on_files
from rag.retriever import retrieve_relevant_context
from agents.finder import run_finder_agent
from agents.exploiter import run_exploiter_agent
from sandbox.docker_runner import run_exploit_in_sandbox
from agents.reviewer import run_remediation_loop
from github_integration.pr_creator import create_pull_request
from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus

logger = logging.getLogger(__name__)


# ── DB Status Update Helper ──────────────────────────────

def update_scan_status(scan_id: int, status: str, extra: dict = None):
    """
    Write current pipeline status to the scans table.
    Called at each step of the pipeline for real-time updates.
    """
    if not scan_id:
        return  # No scan record to update
    
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = status
            if extra:
                if "vulnerability_type" in extra:
                    scan.vulnerability_type = extra["vulnerability_type"]
                if "severity" in extra:
                    scan.severity = extra["severity"]
                if "vulnerable_file" in extra:
                    scan.vulnerable_file = extra["vulnerable_file"]
                if "exploit_output" in extra:
                    scan.exploit_output = extra["exploit_output"]
                if "patch_diff" in extra:
                    scan.patch_diff = extra["patch_diff"]
                if "pr_url" in extra:
                    scan.pr_url = extra["pr_url"]
            db.commit()
            db.refresh(scan)
            _broadcast(scan)
            logger.debug(f"[DB] Scan {scan_id} status updated: {status}")
    except Exception as e:
        logger.warning(f"[DB] Status update failed: {e}")
    finally:
        db.close()


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
            update_scan_status(scan.id, ScanStatus.SCANNING.value)

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
                update_scan_status(scan.id, ScanStatus.CLEAN.value)
            return

        file_paths = [f["filename"] for f in diff["changed_files"]]
        semgrep_findings = run_semgrep_on_files(file_paths, local_repo_path)

        if not semgrep_findings:
            logger.info("✅ Semgrep clean — no issues found.")
            if scan:
                update_scan_status(scan.id, ScanStatus.CLEAN.value)
            return

        logger.warning(f"⚠️  Semgrep: {len(semgrep_findings)} issue(s) → escalating to Agent 1 (Finder)")

        # ── Phase 3: RAG Context ──────────────────────────
        rag_context = retrieve_relevant_context(repo_full_name, diff, semgrep_findings)

        # ── Phase 4: Agent 1 (Finder) — Identify ALL vulnerabilities ─────────────────────
        logger.info("🔍 Agent 1 (Finder): Analyzing code for ALL vulnerabilities...")
        findings = run_finder_agent(diff, semgrep_findings, rag_context)
        
        if not findings:
            logger.info("✅ Finder found no vulnerabilities — clean.")
            if scan:
                update_scan_status(scan.id, ScanStatus.CLEAN.value)
            return
        
        logger.info(f"🔍 Agent 1 (Finder): Found {len(findings)} vulnerabilities")
        
        # Record the most critical finding in the scan
        critical_finding = findings[0]  # Already sorted by severity
        if scan:
            update_scan_status(
                scan.id,
                ScanStatus.SCANNING.value,
                {
                    "vulnerability_type": critical_finding.vuln_type,
                    "severity": critical_finding.severity,
                    "vulnerable_file": critical_finding.file,
                }
            )

        # ── Phase 5: Agent 2 (Exploiter) — Prove each vulnerability ─────────────────────
        confirmed_vulnerabilities = []
        
        for i, finding in enumerate(findings, 1):
            logger.info(f"🎯 Agent 2 (Exploiter): Testing vulnerability {i}/{len(findings)}: {finding.vuln_type}")
            
            if scan:
                update_scan_status(scan.id, ScanStatus.EXPLOITING.value)
            
            # Convert Pydantic model to dict for exploiter
            finding_dict = {
                "file": finding.file,
                "line_start": finding.line_start,
                "vuln_type": finding.vuln_type,
                "severity": finding.severity,
                "description": finding.description,
                "relevant_code": finding.relevant_code,
                "confidence": finding.confidence
            }
            
            exploiter_result = run_exploiter_agent(finding_dict, diff, rag_context)
            exploit_script = exploiter_result["exploit_script"]
            vulnerability_type = exploiter_result["vulnerability_type"]
            
            # Test exploit in Docker sandbox
            exploit_test = run_exploit_in_sandbox(exploit_script, local_repo_path)
            
            if exploit_test["exploit_succeeded"]:
                logger.error(f"🚨 VULNERABILITY CONFIRMED: {vulnerability_type}")
                confirmed_vulnerabilities.append({
                    "finding": finding_dict,
                    "exploit_script": exploit_script,
                    "exploit_output": exploit_test["stdout"],
                    "vulnerability_type": vulnerability_type
                })
                
                if scan:
                    update_scan_status(
                        scan.id,
                        ScanStatus.EXPLOIT_CONFIRMED.value,
                        {"exploit_output": exploit_test["stdout"]}
                    )
                
                # For now, fix the first confirmed vulnerability
                # TODO: Handle multiple vulnerabilities in future
                break
            else:
                logger.info(f"✅ Exploit failed for {vulnerability_type} — likely false positive")
        
        if not confirmed_vulnerabilities:
            logger.info("✅ All exploits failed — no real vulnerabilities confirmed.")
            if scan:
                update_scan_status(
                    scan.id,
                    ScanStatus.FALSE_POSITIVE.value,
                    {"exploit_output": "All exploits failed to confirm vulnerabilities"}
                )
            return
        
        # Work with the first confirmed vulnerability
        confirmed = confirmed_vulnerabilities[0]
        exploit_script = confirmed["exploit_script"]
        exploit_output = confirmed["exploit_output"]
        vulnerability_type = confirmed["vulnerability_type"]
        vulnerable_file = confirmed["finding"]["file"]

        # ── Phase 6+7: Agent 3 (Engineer) + Agent 4 (Verifier) Loop ──────────
        if scan:
            update_scan_status(scan.id, ScanStatus.PATCHING.value)

        full_vulnerable_path = os.path.join(local_repo_path, vulnerable_file)

        with open(full_vulnerable_path, "r") as f:
            original_code = f.read()

        remediation = run_remediation_loop(
            vulnerable_code=original_code,
            file_path=vulnerable_file,
            exploit_script=exploit_script,
            exploit_output=exploit_output,
            vulnerability_type=vulnerability_type,
            repo_path=local_repo_path,
            repo_name=repo_full_name
        )

        if not remediation["success"]:
            logger.error("❌ Agent 3 (Engineer) + Agent 4 (Verifier) failed — human review required.")
            if scan:
                update_scan_status(
                    scan.id,
                    ScanStatus.FAILED.value,
                    {"error_message": "Agents could not generate a working patch after max retries."}
                )
            return

        # ── Phase 8: Open PR ──────────────────────────────
        if scan:
            update_scan_status(scan.id, ScanStatus.VERIFYING.value)

        logger.info("🚀 Opening PR with fix and exploit proof...")
        pr_url = create_pull_request(
            repo_full_name=repo_full_name,
            base_branch=branch,
            file_path=vulnerable_file,
            patched_code=remediation["patched_code"],
            vulnerability_type=vulnerability_type,
            exploit_output=exploit_output,
        )

        if scan:
            update_scan_status(
                scan.id,
                ScanStatus.FIXED.value,
                {
                    "patch_diff": remediation["patched_code"],
                    "pr_url": pr_url
                }
            )

        logger.info(f"🎉 Done! PR: {pr_url}")

    except Exception as e:
        logger.exception(f"Pipeline crashed: {e}")
        if scan:
            try:
                update_scan_status(
                    scan.id,
                    ScanStatus.FAILED.value,
                    {"error_message": str(e)}
                )
            except Exception:
                pass
    finally:
        db.close()

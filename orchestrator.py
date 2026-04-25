import os
import json
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
                if "error_message" in extra:
                    scan.error_message = extra["error_message"]
                if "original_code" in extra:
                    scan.original_code = extra["original_code"]
                if "exploit_script" in extra:
                    scan.exploit_script = extra["exploit_script"]
                if "findings_json" in extra:
                    scan.findings_json = extra["findings_json"]
                if "patch_attempts" in extra:
                    scan.patch_attempts = extra["patch_attempts"]
                # New agent-identity fields
                if "current_agent" in extra:
                    scan.current_agent = extra["current_agent"]
                if "agent_message" in extra:
                    scan.agent_message = extra["agent_message"]
                if "original_code" in extra:
                    scan.original_code = extra["original_code"]
                if "exploit_script" in extra:
                    scan.exploit_script = extra["exploit_script"]
                if "findings_json" in extra:
                    scan.findings_json = extra["findings_json"]
                if "patch_attempts" in extra:
                    scan.patch_attempts = extra["patch_attempts"]
                if "error_message" in extra:
                    scan.error_message = extra["error_message"]
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

    # Reset demo mode exploit counter for this pipeline run
    try:
        from sandbox.docker_runner import _DEMO_EXPLOIT_CALL_COUNT
        _DEMO_EXPLOIT_CALL_COUNT[0] = 0
    except Exception:
        pass

    db = SessionLocal()
    scan = None

    try:
        # Look up repo in DB (may not exist if webhook was manually installed)
        repo_id = _get_repo_id(db, repo_full_name)
        if repo_id:
            scan = _create_scan(db, repo_id, commit_sha, branch)

        # ── Phase 2: Clone + Diff + Semgrep ──────────────
        if scan:
            update_scan_status(scan.id, ScanStatus.SCANNING.value, {
                "current_agent": "finder",
                "agent_message": "Cloning repository and running Semgrep static analysis..."
            })

        local_repo_path = os.path.join(
            config.REPOS_DIR, repo_full_name.replace("/", "_")
        )

        # Use user token if available
        user_token = None
        repo_obj = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
        if repo_obj and repo_obj.user:
            user_token = repo_obj.user.github_token
            clone_url = f"https://x-access-token:{user_token}@github.com/{repo_full_name}.git"
        else:
            clone_url = push_info.get("repo_url", f"https://github.com/{repo_full_name}.git")

        clone_or_pull_repo(clone_url, local_repo_path)

        # Try to get diff from GitHub; fall back to building it from local files
        # if the GitHub API is unavailable (e.g. rate-limited or network issues)
        try:
            diff = get_diff(
                repo_full_name,
                commit_sha,
                github_token=user_token,
                all_changed_files=push_info.get("files_changed", []),
            )
        except Exception as diff_err:
            logger.warning(f"get_diff failed ({diff_err}), building diff from local files")
            diff = {"commit_sha": commit_sha, "commit_message": "", "changed_files": [], "total_changes": 0}

        # If diff is empty but we know which files changed, build synthetic diff from local copies
        if not diff["changed_files"] and push_info.get("files_changed"):
            for fname in push_info["files_changed"]:
                local_fpath = os.path.join(local_repo_path, fname)
                _, ext = os.path.splitext(fname)
                if ext not in config.CODE_EXTENSIONS or not os.path.exists(local_fpath):
                    continue
                with open(local_fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                patch = "\n".join(f"+{line}" for line in content.splitlines())
                diff["changed_files"].append({
                    "filename": fname,
                    "status": "modified",
                    "additions": content.count("\n"),
                    "deletions": 0,
                    "patch": patch,
                })
            logger.info(f"Built synthetic diff for {len(diff['changed_files'])} file(s) from local repo")

        if not diff["changed_files"]:
            logger.info("No supported code files changed. Pipeline done.")
            if scan:
                update_scan_status(scan.id, ScanStatus.CLEAN.value)
            return

        file_paths = [f["filename"] for f in diff["changed_files"]]

        # ── Phase 3: Semgrep + RAG in parallel ───────────
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=2) as pool:
            semgrep_future = pool.submit(run_semgrep_on_files, file_paths, local_repo_path)
            # RAG needs semgrep results for query building — start with empty list,
            # then re-retrieve after semgrep if findings exist (fast second call)
            rag_future = pool.submit(retrieve_relevant_context, repo_full_name, diff, [])
            semgrep_findings = semgrep_future.result()
            rag_context = rag_future.result()

        # If semgrep found things, do a quick targeted RAG re-query
        if semgrep_findings:
            logger.warning(f"⚠️  Semgrep: {len(semgrep_findings)} issue(s) → escalating to Agent 1 (Finder)")
            rag_context = retrieve_relevant_context(repo_full_name, diff, semgrep_findings)
        else:
            logger.info("Semgrep found nothing — still running Finder agent for deeper analysis...")

        # ── Phase 4: Agent 1 (Finder) — Identify ALL vulnerabilities ─────────────────────
        logger.info("🔍 Agent 1 (Finder): Analyzing code for ALL vulnerabilities...")
        if scan:
            update_scan_status(scan.id, ScanStatus.SCANNING.value, {
                "current_agent": "finder",
                "agent_message": f"Analyzing {len(semgrep_findings)} Semgrep finding(s) + RAG context..." if semgrep_findings else "Running deep AI analysis (Semgrep found nothing)..."
            })
        findings = run_finder_agent(diff, semgrep_findings, rag_context)
        
        if not findings:
            logger.info("✅ Finder found no vulnerabilities — clean.")
            if scan:
                update_scan_status(scan.id, ScanStatus.CLEAN.value, {
                    "current_agent": None,
                    "agent_message": "No vulnerabilities found — code is clean!"
                })
            return
        
        logger.info(f"🔍 Agent 1 (Finder): Found {len(findings)} vulnerabilities")
        
        # Record the most critical finding in the scan
        critical_finding = findings[0]  # Already sorted by severity
        if scan:
            update_scan_status(
                scan.id,
                ScanStatus.SCANNING.value,
                {
                    "current_agent": "finder",
                    "agent_message": f"Found {len(findings)} vulnerabilit{'y' if len(findings)==1 else 'ies'} — most critical: {critical_finding.vuln_type}",
                    "vulnerability_type": critical_finding.vuln_type,
                    "severity": critical_finding.severity,
                    "vulnerable_file": critical_finding.file,
                    "findings_json": json.dumps([f.dict() for f in findings]),
                }
            )

        # ── Phase 5: Agent 2 (Exploiter) — Prove each vulnerability ─────────────────────
        confirmed_vulnerabilities = []
        
        for i, finding in enumerate(findings, 1):
            logger.info(f"🎯 Agent 2 (Exploiter): Testing vulnerability {i}/{len(findings)}: {finding.vuln_type}")
            
            if scan:
                update_scan_status(scan.id, ScanStatus.EXPLOITING.value, {
                    "current_agent": "exploiter",
                    "agent_message": f"Writing exploit for {finding.vuln_type} in {finding.file}:{finding.line_start}..."
                })
            
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
            
            if scan:
                update_scan_status(scan.id, ScanStatus.EXPLOITING.value, {
                    "current_agent": "exploiter",
                    "agent_message": f"Running exploit in isolated Docker sandbox...",
                    "exploit_script": exploit_script
                })
            
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
                        {
                            "current_agent": "exploiter",
                            "agent_message": f"CONFIRMED: {vulnerability_type} is exploitable in Docker sandbox",
                            "exploit_output": exploit_test["stdout"],
                        }
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
                    {
                        "current_agent": None,
                        "agent_message": "All exploits failed to confirm vulnerabilities — marked as false positive",
                        "exploit_output": "All exploits failed to confirm vulnerabilities"
                    }
                )
            return
        
        # Work with the first confirmed vulnerability
        confirmed = confirmed_vulnerabilities[0]
        exploit_script = confirmed["exploit_script"]
        exploit_output = confirmed["exploit_output"]
        vulnerability_type = confirmed["vulnerability_type"]
        vulnerable_file = confirmed["finding"]["file"]

        full_vulnerable_path = os.path.join(local_repo_path, vulnerable_file)

        with open(full_vulnerable_path, "r") as f:
            original_code = f.read()

        # ── Phase 6+7: Agent 3 (Engineer) + Agent 4 (Verifier) Loop ──────────
        if scan:
            update_scan_status(scan.id, ScanStatus.PATCHING.value, {
                "current_agent": "engineer",
                "agent_message": f"Writing security patch for {vulnerable_file}...",
                "original_code": original_code,
                "patch_attempts": 0
            })

        remediation = run_remediation_loop(
            vulnerable_code=original_code,
            file_path=vulnerable_file,
            exploit_script=exploit_script,
            exploit_output=exploit_output,
            vulnerability_type=vulnerability_type,
            repo_path=local_repo_path,
            repo_name=repo_full_name,
            scan_id=scan.id if scan else None,
            update_status_fn=update_scan_status,
        )

        if not remediation["success"]:
            logger.error("❌ Agent 3 (Engineer) + Agent 4 (Verifier) failed — human review required.")
            if scan:
                update_scan_status(
                    scan.id,
                    ScanStatus.FAILED.value,
                    {
                        "current_agent": None,
                        "agent_message": f"Failed after {remediation.get('attempts', 3)} attempt(s) — human review required",
                        "error_message": "Agents could not generate a working patch after max retries.",
                        "patch_attempts": remediation.get('attempts', 3)
                    }
                )
            return

        # ── Phase 8: Open PR ──────────────────────────────
        if scan:
            update_scan_status(scan.id, ScanStatus.VERIFYING.value, {
                "current_agent": "verifier",
                "agent_message": "Patch verified — exploit blocked, tests passing. Opening PR...",
                "patch_attempts": remediation.get('attempts', 1)
            })

        logger.info("🚀 Opening PR with fix and exploit proof...")
        try:
            pr_url = create_pull_request(
                repo_full_name=repo_full_name,
                base_branch=branch,
                file_path=vulnerable_file,
                patched_code=remediation["patched_code"],
                vulnerability_type=vulnerability_type,
                exploit_output=exploit_output,
            )
        except Exception as pr_err:
            logger.error(f"❌ PR creation failed: {pr_err}")
            # Still mark as fixed — the patch is good even if PR failed
            pr_url = None
            if scan:
                update_scan_status(scan.id, ScanStatus.FIXED.value, {
                    "current_agent": None,
                    "agent_message": f"Patch verified! PR creation failed: {pr_err}",
                    "patch_diff": remediation["patched_code"],
                    "patch_attempts": remediation.get('attempts', 1),
                    "error_message": f"PR creation failed: {pr_err}",
                })
            return

        if scan:
            update_scan_status(
                scan.id,
                ScanStatus.FIXED.value,
                {
                    "current_agent": None,
                    "agent_message": "Vulnerability fixed! Exploit blocked, tests passing. PR opened.",
                    "patch_diff": remediation["patched_code"],
                    "pr_url": pr_url,
                    "patch_attempts": remediation.get('attempts', 1)
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

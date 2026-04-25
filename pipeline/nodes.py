"""
Aegis Pipeline Nodes

Each function here is one "step" in the LangGraph pipeline.
A node receives the full pipeline state, does its work, and returns
a dict with ONLY the fields it changed — LangGraph merges the rest.

Node order:
  pre_process → finder → exploiter → engineer → verifier → pr_creator

Routing between nodes is handled in graph.py.
"""

import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import config
from pipeline.state import AegisPipelineState
from database.models import ScanStatus
from orchestrator import update_scan_status  # reuse existing DB/SSE helper

# Agents
from agents.triage import run_triage_agent
from agents.finder import run_finder_agent
from agents.exploiter import run_exploiter_agent
from agents.reviewer import run_remediation_loop

# Infrastructure
from github_integration.diff_fetcher import clone_or_pull_repo, get_diff
from scanner.semgrep_runner import run_semgrep_on_files
from rag.retriever import retrieve_relevant_context
from sandbox.docker_runner import run_exploit_in_sandbox
from github_integration.pr_creator import create_pull_request, post_pr_review, get_pr_changed_files
from utils.crypto import decrypt_token
from database.db import SessionLocal
from database.models import Repo, Scan
from scanner.dependency_scanner import scan_dependencies

logger = logging.getLogger(__name__)


def _run_dependency_scan(repo_path: str) -> list[dict]:
    """Wrapper so dependency scan errors don't crash the pipeline."""
    try:
        return scan_dependencies(repo_path)
    except Exception as e:
        logger.warning(f"Dependency scan failed: {e}")
        return []


# ── Node 1: Pre-process ───────────────────────────────────

def pre_process_node(state: AegisPipelineState) -> dict:
    """
    Clone the repo, fetch the git diff, run Semgrep and RAG in parallel.
    This is the setup step — no AI agents yet.
    """
    repo_full_name = state["repo_full_name"]
    commit_sha     = state["commit_sha"]
    push_info      = state["push_info"]
    scan_id        = state["scan_id"]

    if scan_id:
        update_scan_status(scan_id, ScanStatus.SCANNING.value, {
            "current_agent": "finder",
            "agent_message": "Cloning repository and running Semgrep analysis...",
        })

    # ── Clone / pull the repo ─────────────────────────────
    local_repo_path = os.path.join(
        config.REPOS_DIR, repo_full_name.replace("/", "_")
    )

    # Use the user's decrypted token if available, else fall back to push_info URL
    user_token = None
    db = SessionLocal()
    try:
        repo_obj = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
        if repo_obj and repo_obj.user:
            user_token = decrypt_token(repo_obj.user.github_token)
            clone_url = f"https://x-access-token:{user_token}@github.com/{repo_full_name}.git"
        else:
            clone_url = push_info.get("repo_url", f"https://github.com/{repo_full_name}.git")
    finally:
        db.close()

    clone_or_pull_repo(clone_url, local_repo_path)

    # ── Get the diff ──────────────────────────────────────
    # For PR scans, fetch files directly from the PR API (more accurate than commit diff)
    is_pr = push_info.get("is_pr", False)
    pr_number = push_info.get("pr_number")

    if is_pr and pr_number:
        logger.info(f"PR scan mode: fetching changed files for PR #{pr_number}")
        try:
            pr_files = get_pr_changed_files(repo_full_name, pr_number)
            diff = {
                "commit_sha": commit_sha,
                "commit_message": f"PR #{pr_number}",
                "changed_files": pr_files,
                "total_changes": sum(f["additions"] + f["deletions"] for f in pr_files),
            }
        except Exception as e:
            logger.warning(f"PR file fetch failed ({e}) — falling back to commit diff")
            diff = None
    else:
        diff = None

    if diff is None:
        try:
            diff = get_diff(
                repo_full_name,
                commit_sha,
                github_token=user_token,
                all_changed_files=push_info.get("files_changed", []),
            )
        except Exception as e:
            logger.warning(f"get_diff failed ({e}) — building synthetic diff from local files")
            diff = {"commit_sha": commit_sha, "commit_message": "", "changed_files": [], "total_changes": 0}

    # Build synthetic diff from local files if GitHub API returned nothing
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

    if not diff["changed_files"]:
        logger.info("No supported code files changed.")
        return {
            "local_repo_path": local_repo_path,
            "diff": diff,
            "semgrep_findings": [],
            "rag_context": "",
            "pipeline_status": "clean",
        }

    # ── Triage: quick classification before full scan ─────
    # If the commit is docs-only or clearly non-security, skip the pipeline.
    triage = run_triage_agent(diff)
    if triage.skip_scan:
        logger.info(f"Triage: skipping scan — {triage.analysis_brief}")
        if scan_id:
            update_scan_status(scan_id, ScanStatus.CLEAN.value, {
                "current_agent": None,
                "agent_message": f"Triage: {triage.analysis_brief}",
            })
        return {
            "local_repo_path": local_repo_path,
            "diff": diff,
            "semgrep_findings": [],
            "rag_context": "",
            "pipeline_status": "clean",
        }

    logger.info(
        f"Triage: priority={triage.scan_priority}, "
        f"domains={triage.security_domains}. Proceeding with scan."
    )

    # ── Semgrep + RAG + Dependency scan in parallel ──────
    file_paths = [f["filename"] for f in diff["changed_files"]]
    with ThreadPoolExecutor(max_workers=3) as pool:
        semgrep_future = pool.submit(run_semgrep_on_files, file_paths, local_repo_path)
        rag_future     = pool.submit(retrieve_relevant_context, repo_full_name, diff, [])
        dep_future     = pool.submit(_run_dependency_scan, local_repo_path)
        semgrep_findings = semgrep_future.result()
        rag_context      = rag_future.result()
        dep_vulns        = dep_future.result()

    # If Semgrep found things, do a targeted RAG re-query for better context
    if semgrep_findings:
        rag_context = retrieve_relevant_context(repo_full_name, diff, semgrep_findings)

    # Log dependency vulnerabilities found
    if dep_vulns:
        logger.warning(f"Dependency scan: {len(dep_vulns)} vulnerable package(s) found")

    return {
        "local_repo_path": local_repo_path,
        "diff": diff,
        "semgrep_findings": semgrep_findings,
        "rag_context": rag_context,
        "dependency_vulns": dep_vulns,
        "pipeline_status": "scanning",
    }


# ── Node 2: Finder ────────────────────────────────────────

def finder_node(state: AegisPipelineState) -> dict:
    """
    Run Agent 1 (Finder) to identify ALL vulnerabilities in the diff.
    """
    scan_id = state["scan_id"]
    semgrep_findings = state.get("semgrep_findings", [])

    if scan_id:
        update_scan_status(scan_id, ScanStatus.SCANNING.value, {
            "current_agent": "finder",
            "agent_message": (
                f"Analyzing {len(semgrep_findings)} Semgrep finding(s) + RAG context..."
                if semgrep_findings
                else "Running deep AI analysis..."
            ),
        })

    findings = run_finder_agent(
        state["diff"],
        semgrep_findings,
        state.get("rag_context", ""),
    )

    if not findings:
        logger.info("Finder found no vulnerabilities — clean.")
        if scan_id:
            update_scan_status(scan_id, ScanStatus.CLEAN.value, {
                "current_agent": None,
                "agent_message": "No vulnerabilities found — code is clean!",
            })
        return {
            "vulnerability_findings": [],
            "pipeline_status": "clean",
        }

    # Record the most critical finding for the DB/UI
    critical = findings[0]  # already sorted by severity
    if scan_id:
        update_scan_status(scan_id, ScanStatus.SCANNING.value, {
            "current_agent": "finder",
            "agent_message": (
                f"Found {len(findings)} vulnerabilit{'y' if len(findings)==1 else 'ies'} "
                f"— most critical: {critical.vuln_type}"
            ),
            "vulnerability_type": critical.vuln_type,
            "severity": critical.severity,
            "vulnerable_file": critical.file,
            "findings_json": json.dumps([f.dict() for f in findings]),
        })

    return {
        "vulnerability_findings": [f.dict() for f in findings],
        "pipeline_status": "scanning",
    }


# ── Node 3: Exploiter ─────────────────────────────────────

def exploiter_node(state: AegisPipelineState) -> dict:
    """
    Run Agent 2 (Exploiter) on every finding.
    Collects ALL confirmed vulnerabilities (no early stop).
    """
    scan_id  = state["scan_id"]
    findings = state.get("vulnerability_findings", [])
    diff     = state["diff"]
    rag      = state.get("rag_context", "")
    repo_path = state["local_repo_path"]

    confirmed = []
    exploit_artifacts = state.get("exploit_artifacts", []) or []

    for i, finding in enumerate(findings, 1):
        vuln_type = finding.get("vuln_type", "Unknown")
        logger.info(f"Exploiter: testing {i}/{len(findings)}: {vuln_type}")

        if scan_id:
            update_scan_status(scan_id, ScanStatus.EXPLOITING.value, {
                "current_agent": "exploiter",
                "agent_message": (
                    f"Testing {i}/{len(findings)}: {vuln_type} "
                    f"in {finding.get('file')}:{finding.get('line_start')}..."
                ),
            })

        result = run_exploiter_agent(finding, diff, rag)
        exploit_script    = result["exploit_script"]
        vulnerability_type = result["vulnerability_type"]

        if scan_id:
            update_scan_status(scan_id, ScanStatus.EXPLOITING.value, {
                "current_agent": "exploiter",
                "agent_message": "Running exploit in Docker sandbox...",
                "exploit_script": exploit_script,
            })

        sandbox = run_exploit_in_sandbox(exploit_script, repo_path)

        # Hard stop if Docker is unavailable
        if "SANDBOX_UNAVAILABLE" in sandbox.get("stderr", ""):
            logger.error("Docker unavailable — aborting.")
            if scan_id:
                update_scan_status(scan_id, ScanStatus.FAILED.value, {
                    "current_agent": None,
                    "agent_message": "Docker is not running — scan aborted.",
                    "error_message": "Docker daemon unavailable. Start Docker and retry.",
                })
            return {
                "confirmed_vulnerabilities": [],
                "pipeline_status": "failed",
                "error": "Docker unavailable",
            }

        if sandbox["exploit_succeeded"]:
            logger.error(f"CONFIRMED: {vulnerability_type}")
            confirmed.append({
                "finding": finding,
                "exploit_script": exploit_script,
                "exploit_output": sandbox["stdout"],
                "vulnerability_type": vulnerability_type,
            })
            exploit_artifacts.append({
                "finding_index": i,
                "exploit_script": exploit_script,
                "sandbox_stdout": sandbox["stdout"],
                "sandbox_stderr": sandbox.get("stderr", ""),
                "vulnerability_type": vulnerability_type,
            })
            if scan_id:
                update_scan_status(scan_id, ScanStatus.EXPLOIT_CONFIRMED.value, {
                    "current_agent": "exploiter",
                    "agent_message": f"Confirmed {i}/{len(findings)}: {vulnerability_type} is exploitable",
                    "exploit_output": sandbox["stdout"],
                })
        else:
            logger.info(f"Exploit failed for {vulnerability_type} — false positive")

    if not confirmed:
        if scan_id:
            update_scan_status(scan_id, ScanStatus.FALSE_POSITIVE.value, {
                "current_agent": None,
                "agent_message": "All exploits failed — false positive",
                "exploit_output": "No exploits succeeded",
            })
        return {
            "confirmed_vulnerabilities": [],
            "pipeline_status": "false_positive",
        }

    return {
        "confirmed_vulnerabilities": confirmed,
        "exploit_artifacts": exploit_artifacts,
        "current_vuln_index": 0,
        "pipeline_status": "exploiting",
    }


# ── Node 4: Engineer ──────────────────────────────────────

def engineer_node(state: AegisPipelineState) -> dict:
    """
    Run the Engineer→Verifier remediation loop for the current vulnerability.
    Advances current_vuln_index when done.
    
    For CRITICAL severity vulnerabilities, sets status to AWAITING_APPROVAL
    instead of proceeding directly to PR creation.
    """
    scan_id   = state["scan_id"]
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx       = state.get("current_vuln_index", 0)
    repo_path = state["local_repo_path"]
    repo_name = state["repo_full_name"]

    if idx >= len(confirmed):
        # All vulnerabilities processed
        return {"pipeline_status": "all_fixed"}

    vuln = confirmed[idx]
    vuln_type  = vuln["vulnerability_type"]
    vuln_file  = vuln["finding"]["file"]
    vuln_severity = vuln["finding"].get("severity", "").upper()
    exploit_sc = vuln["exploit_script"]
    exploit_out = vuln["exploit_output"]

    logger.info(f"Engineer: fixing {idx+1}/{len(confirmed)}: {vuln_type} in {vuln_file}")

    full_path = os.path.join(repo_path, vuln_file)
    with open(full_path, "r") as f:
        original_code = f.read()

    if scan_id:
        update_scan_status(scan_id, ScanStatus.PATCHING.value, {
            "current_agent": "engineer",
            "agent_message": f"Patching {idx+1}/{len(confirmed)}: {vuln_type} in {vuln_file}...",
            "original_code": original_code,
            "patch_attempts": 0,
            "vulnerability_type": vuln_type,
            "vulnerable_file": vuln_file,
        })

    remediation = run_remediation_loop(
        vulnerable_code=original_code,
        file_path=vuln_file,
        exploit_script=exploit_sc,
        exploit_output=exploit_out,
        vulnerability_type=vuln_type,
        repo_path=repo_path,
        repo_name=repo_name,
        scan_id=scan_id,
        update_status_fn=update_scan_status,
        safety_report=state.get("safety_report"),
    )

    if not remediation["success"]:
        logger.error(f"Could not patch {vuln_type} — skipping.")
        if scan_id:
            update_scan_status(scan_id, ScanStatus.FAILED.value, {
                "current_agent": None,
                "agent_message": f"Failed to patch {vuln_type} — human review needed",
                "error_message": f"Could not patch {vuln_type}",
                "patch_attempts": remediation.get("attempts", 3),
            })
        return {
            "verification_passed": False,
            "current_vuln_index": idx + 1,  # move to next vuln
            "pipeline_status": "patching",
        }

    patch_artifacts = state.get("patch_artifacts", []) or []
    patch_artifacts.append({
        "vulnerability_type": vuln_type,
        "patched_code": remediation.get("patched_code"),
        "test_code": remediation.get("test_code"),
        "attempts": remediation.get("attempts"),
        "test_output": remediation.get("test_output"),
        "error_artifacts": remediation.get("error_artifacts", []),
    })

    return {
        "patched_code": remediation["patched_code"],
        "test_code": remediation["test_code"],
        "original_code": original_code,
        "verification_passed": True,
        "retry_count": 0,
        "current_vuln_index": idx,
        "pipeline_status": "patching",
        "patch_artifacts": patch_artifacts,
    }

# ── Node: Approval Gate ───────────────────────────────────

def approval_gate_node(state: AegisPipelineState) -> dict:
    """
    Checks if the patched vulnerability is CRITICAL and requires human approval.
    Runs after safety validation.
    """
    scan_id = state.get("scan_id")
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx = state.get("current_vuln_index", 0)

    if idx >= len(confirmed):
        return {}

    vuln = confirmed[idx]
    vuln_severity = vuln["finding"].get("severity", "").upper()
    vuln_type = vuln["vulnerability_type"]

    if vuln_severity == "CRITICAL" and scan_id:
        logger.info(f"CRITICAL vulnerability detected — awaiting human approval")
        update_scan_status(scan_id, ScanStatus.AWAITING_APPROVAL.value, {
            "current_agent": None,
            "agent_message": f"CRITICAL {vuln_type} patched — awaiting human approval",
            "patch_diff": state.get("patched_code"),
        })
        return {
            "awaiting_approval": True,
            "pipeline_status": "awaiting_approval",
        }

    return {
        "awaiting_approval": False,
    }


# ── Node 5: PR Creator ────────────────────────────────────

def pr_creator_node(state: AegisPipelineState) -> dict:
    """
    For push scans: open a GitHub PR with the fix.
    For PR scans: post inline review comments on the existing PR.
    """
    scan_id   = state["scan_id"]
    confirmed = state.get("confirmed_vulnerabilities", [])
    idx       = state.get("current_vuln_index", 0)
    branch    = state["branch"]
    repo_name = state["repo_full_name"]
    pr_urls   = list(state.get("pr_urls", []))
    push_info = state.get("push_info", {})

    vuln      = confirmed[idx]
    vuln_type = vuln["vulnerability_type"]
    vuln_file = vuln["finding"]["file"]
    is_pr     = push_info.get("is_pr", False)
    pr_number = push_info.get("pr_number")

    if scan_id:
        update_scan_status(scan_id, ScanStatus.VERIFYING.value, {
            "current_agent": "verifier",
            "agent_message": (
                f"Patch verified — {'posting PR review' if is_pr else 'opening PR'} for {vuln_type}..."
            ),
        })

    try:
        if is_pr and pr_number:
            # PR scan mode — post inline review comments on the existing PR
            pr_url = post_pr_review(
                repo_full_name=repo_name,
                pr_number=pr_number,
                commit_sha=state["commit_sha"],
                findings=state.get("vulnerability_findings", []),
                patched_code=state.get("patched_code"),
                vulnerable_file=vuln_file,
                vulnerability_type=vuln_type,
                exploit_output=vuln.get("exploit_output"),
            )
            logger.info(f"PR review posted: {pr_url}")
        else:
            # Push scan mode — create a new PR with the fix
            pr_url = create_pull_request(
                repo_full_name=repo_name,
                base_branch=branch,
                file_path=vuln_file,
                patched_code=state["patched_code"],
                vulnerability_type=vuln_type,
                exploit_output=vuln["exploit_output"],
            )
            logger.info(f"PR opened: {pr_url}")

        pr_urls.append(pr_url)
    except Exception as e:
        logger.error(f"PR creation/review failed: {e}")
        pr_url = None

    if scan_id:
        update_scan_status(scan_id, ScanStatus.FIXED.value, {
            "current_agent": None,
            "agent_message": (
                f"Fixed {idx+1}/{len(confirmed)}: {vuln_type}. "
                + (f"PR: {pr_url}" if pr_url else "PR creation failed.")
            ),
            "patch_diff": state["patched_code"],
            "pr_url": pr_url,
        })

    # Save this successful fix to the pattern library so future scans learn from it
    try:
        from intelligence.vuln_patterns import save_learned_pattern
        save_learned_pattern(
            vuln_type=vuln_type,
            vulnerable_code=state.get("original_code", ""),
            patched_code=state.get("patched_code", ""),
            file_path=vuln_file,
        )
    except Exception as e:
        logger.warning(f"Could not save learned pattern: {e}")

    # Record the fix as a regression signature so future scans can detect regressions
    try:
        from intelligence.regression_detector import record_fix
        if scan_id:
            _db = SessionLocal()
            try:
                _scan_obj = _db.query(Scan).filter(Scan.id == scan_id).first()
                repo_id = _scan_obj.repo_id if _scan_obj else None
            finally:
                _db.close()
            if repo_id:
                record_fix(
                    repo_id=repo_id,
                    file_path=vuln_file,
                    vuln_type=vuln_type,
                    severity=vuln["finding"].get("severity", "HIGH"),
                    fix_commit=state["commit_sha"],
                    fix_scan_id=scan_id,
                )
    except Exception as e:
        logger.warning(f"Could not record regression signature: {e}")

    return {
        "pr_urls": pr_urls,
        "current_vuln_index": idx + 1,
        "pipeline_status": "fixed",
    }

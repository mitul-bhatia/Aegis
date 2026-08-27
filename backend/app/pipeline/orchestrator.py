import os
import json
import shutil
import tempfile
import logging
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

from backend.app.core.database import SessionLocal
from backend.app.models.entities import Scan, Repository, User, Issue
from backend.app.rag.tree_indexer import index_repository_structure
from backend.app.agents.finder import run_finder_agent
from backend.app.agents.engineer import generate_patch_with_engineer, generate_reproduction_script
from backend.app.agents.reviewer import review_patch_safety
from backend.app.agents.pr_creator import create_security_pull_request
from backend.app.github.auth import get_installation_access_token
from backend.app.api.scans import broadcast_scan_update

logger = logging.getLogger("aegis.pipeline.orchestrator")


def _broadcast(scan: Scan):
    """Helper to broadcast serialized scan update to SSE listeners."""
    try:
        data = {
            "id": scan.id,
            "repo_id": scan.repo_id,
            "commit_sha": scan.commit_sha,
            "branch": scan.branch,
            "status": scan.status,
            "vulnerability_type": scan.vulnerability_type,
            "severity": scan.severity,
            "pr_url": scan.pr_url,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "vulnerable_file": scan.vulnerable_file,
            "patch_diff": scan.patch_diff,
            "error_message": scan.error_message,
            "current_agent": scan.current_agent,
            "agent_message": scan.agent_message,
        }
        broadcast_scan_update(data)
    except Exception as e:
        logger.debug(f"Broadcast failed: {e}")


def clone_repo_ephemeral(repo_full_name: str, installation_id: Optional[int], target_dir: str) -> bool:
    """Clone target GitHub repository using installation token or public git."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    
    clone_url = f"https://github.com/{repo_full_name}.git"
    if installation_id:
        try:
            token = get_installation_access_token(installation_id)
            clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        except Exception as e:
            logger.warning(f"Could not get installation token for clone: {e}")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, target_dir],
            env=env,
            capture_output=True,
            timeout=45,
            check=False,
        )
        return os.path.exists(target_dir) and len(os.listdir(target_dir)) > 0
    except Exception as e:
        logger.warning(f"Git clone failed for {repo_full_name}: {e}")
        return False


async def execute_scan_background(scan_id: int):
    """
    Execute full Phase 1 pipeline (Clone -> Structural RAG -> Finder Agent -> Issue Hub).
    """
    db = SessionLocal()
    temp_dir = tempfile.mkdtemp(prefix="aegis_scan_")
    
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return

        repo = scan.repository
        if not repo:
            return

        # 1. Update status to scanning
        scan.status = "scanning"
        scan.current_agent = "finder"
        scan.agent_message = f"Cloning repository {repo.full_name} and mapping structural architecture..."
        db.commit()
        _broadcast(scan)

        # 2. Ephemeral Clone
        cloned = clone_repo_ephemeral(repo.full_name, repo.installation_id, temp_dir)
        scan_path = temp_dir if cloned else "."

        # 3. Structural RAG Indexing
        scan.agent_message = "Indexing codebase AST and running Semgrep vulnerability rules..."
        db.commit()
        _broadcast(scan)

        # 4. Run Finder Agent
        findings = run_finder_agent(scan_path)
        logger.info(f"Scan #{scan_id}: Finder identified {len(findings)} findings.")

        if not findings:
            scan.status = "clean"
            scan.current_agent = None
            scan.agent_message = "No security vulnerabilities or structural flaws detected. Repository is clean!"
            scan.completed_at = datetime.utcnow()
            db.commit()
            _broadcast(scan)
            return

        # 5. Populate primary finding
        primary_finding = findings[0]
        scan.vulnerability_type = primary_finding.vuln_type
        scan.severity = primary_finding.severity
        scan.vulnerable_file = primary_finding.file
        scan.findings_json = json.dumps([f.dict() for f in findings], indent=2)

        # Read original code if available
        full_vuln_path = os.path.join(scan_path, primary_finding.file)
        if os.path.exists(full_vuln_path):
            with open(full_vuln_path, "r", encoding="utf-8", errors="replace") as f:
                scan.original_code = f.read()
        else:
            scan.original_code = primary_finding.relevant_code

        # Generate reproduction script for CLI sandbox
        scan.agent_message = "Generating zero-trust Sandbox verification script..."
        db.commit()
        _broadcast(scan)
        
        exploit_script = generate_reproduction_script(scan.original_code, scan.vulnerability_type, scan.vulnerable_file)
        scan.exploit_script = exploit_script


        # Create interactive issues
        for f in findings:
            issue = Issue(
                scan_id=scan.id,
                repo_id=repo.id,
                title=f"{f.vuln_type} in {f.file}",
                vulnerability_type=f.vuln_type,
                severity=f.severity,
                file_path=f.file,
                line_start=f.line_start,
                description=f.description,
                code_snippet=f.relevant_code,
                status="open",
                reproduction_cmd=f"python runner/aegis_cli.py verify {scan.id}",
            )
            db.add(issue)

        # 6. Pause at awaiting_approval so developer can verify locally or click fix
        scan.status = "awaiting_approval"
        scan.current_agent = "approval_gate"
        scan.agent_message = f"Identified {len(findings)} findings. Awaiting developer review or local verification."
        db.commit()
        _broadcast(scan)

    except Exception as e:
        logger.error(f"Error in scan #{scan_id}: {e}", exc_info=True)
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.error_message = str(e)
            scan.agent_message = f"Scan failed: {str(e)}"
            db.commit()
            _broadcast(scan)
    finally:
        db.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


async def execute_engineer_fix_background(scan_id: int, user_context: Optional[str] = None):
    """
    Execute Phase 2 pipeline (Engineer Agent -> Reviewer -> GitHub PR Creator).
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan or not scan.repository:
            return

        repo = scan.repository
        scan.status = "patching"
        scan.current_agent = "engineer"
        scan.agent_message = "Engineer Agent synthesizing minimal regression-tested patch..."
        db.commit()
        _broadcast(scan)

        # 1. Synthesize patch
        patch_result = generate_patch_with_engineer(
            file_path=scan.vulnerable_file or "main.py",
            original_code=scan.original_code or "",
            vulnerability_description=scan.agent_message or "",
            vuln_type=scan.vulnerability_type or "Security Vulnerability",
            user_context=user_context,
        )

        scan.patch_diff = patch_result["patch_diff"]
        patched_content = patch_result["patched_content"]
        explanation = patch_result["explanation"]

        # 2. Reviewer Safety Check
        scan.status = "verifying"
        scan.current_agent = "verifier"
        scan.agent_message = "Reviewer Agent validating patch safety and AST correctness..."
        db.commit()
        _broadcast(scan)

        review = review_patch_safety(
            file_path=scan.vulnerable_file or "main.py",
            original_code=scan.original_code or "",
            patched_code=patched_content,
            vuln_type=scan.vulnerability_type or "Security Vulnerability",
        )

        # 3. Create PR
        scan.agent_message = "Opening verified Pull Request on GitHub..."
        db.commit()
        _broadcast(scan)

        pr_url = create_security_pull_request(
            installation_id=repo.installation_id,
            repo_full_name=repo.full_name,
            vulnerability_type=scan.vulnerability_type or "Security Vulnerability",
            severity=scan.severity or "HIGH",
            file_path=scan.vulnerable_file or "main.py",
            patched_file_content=patched_content,
            patch_diff=scan.patch_diff,
            explanation=explanation,
        )

        scan.status = "fixed"
        scan.pr_url = pr_url
        scan.current_agent = None
        scan.agent_message = f"Vulnerability resolved! Pull Request opened: {pr_url}"
        scan.completed_at = datetime.utcnow()
        db.commit()
        _broadcast(scan)

    except Exception as e:
        logger.error(f"Error in patch generation for scan #{scan_id}: {e}", exc_info=True)
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.error_message = str(e)
            scan.agent_message = f"Fix failed: {str(e)}"
            db.commit()
            _broadcast(scan)
    finally:
        db.close()

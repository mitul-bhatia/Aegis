import os
import logging
import config

from github.diff_fetcher import clone_or_pull_repo, get_diff
from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm
from rag.retriever import retrieve_relevant_context
from agents.hacker import run_hacker_agent
from sandbox.docker_runner import run_exploit_in_sandbox
from agents.reviewer import run_remediation_loop
from github.pr_creator import create_pull_request

logger = logging.getLogger(__name__)

def run_aegis_pipeline(push_info: dict):
    """
    The main Aegis pipeline that coordinates all phases.
    This runs in the background after a webhook is received.
    """
    repo_full_name = push_info["repo_name"]
    commit_sha = push_info["commit_sha"]
    branch = push_info["branch"]
    
    logger.info(f"=== Starting Aegis Pipeline for {repo_full_name} @ {commit_sha[:8]} ===")
    
    try:
        # Phase 2: Diff & Scanner
        local_repo_path = os.path.join(config.REPOS_DIR, repo_full_name.replace("/", "_"))
        clone_or_pull_repo(push_info["repo_url"], local_repo_path)
        
        diff = get_diff(repo_full_name, commit_sha)
        
        if not diff["changed_files"]:
            logger.info("No supported code files changed. Exiting pipeline.")
            return
            
        file_paths = [f["filename"] for f in diff["changed_files"]]
        semgrep_findings = run_semgrep_on_files(file_paths, local_repo_path)
        
        if not semgrep_findings:
            logger.info("✅ Semgrep found no issues. Code looks clean. Exiting.")
            return
            
        logger.warning(f"⚠️ Semgrep found {len(semgrep_findings)} potential issues. Escalating to Agent A.")
        
        # Phase 3: RAG Memory
        rag_context = retrieve_relevant_context(repo_full_name, diff, semgrep_findings)
        
        # Phase 4: Agent A (Hacker)
        hacker_result = run_hacker_agent(diff, semgrep_findings, rag_context)
        exploit_script = hacker_result["exploit_script"]
        vulnerability_type = hacker_result["vulnerability_type"]
        
        # Phase 5: Docker Sandbox (Initial Exploit Test)
        exploit_test = run_exploit_in_sandbox(exploit_script, local_repo_path)
        
        if not exploit_test["exploit_succeeded"]:
            logger.info("✅ Agent A could not exploit the vulnerability. Likely a false positive. Exiting.")
            return
            
        logger.error(f"🚨 VULNERABILITY CONFIRMED: {vulnerability_type} is exploitable!")
        
        # Phase 6 & 7: Agent B (Engineer) & Agent C (Reviewer) remediation loop
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
            repo_path=local_repo_path
        )
        
        if not remediation["success"]:
            logger.error("❌ Remediation failed. Could not generate a working patch. Human review required.")
            return
            
        # Phase 8: PR Creator
        logger.info("🚀 Opening Pull Request with fix and proof...")
        pr_url = create_pull_request(
            repo_full_name=repo_full_name,
            base_branch=branch,
            file_path=vulnerable_file,
            patched_code=remediation["patched_code"],
            vulnerability_type=vulnerability_type,
            exploit_output=exploit_test["stdout"]
        )
        
        logger.info(f"🎉 Pipeline complete! PR URL: {pr_url}")
        
    except Exception as e:
        logger.exception(f"Pipeline crashed with unhandled exception: {e}")
        # In a production system, we would alert the team here

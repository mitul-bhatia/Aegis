import subprocess
import json
import os
import logging
import shutil

import config

logger = logging.getLogger(__name__)


def _resolve_semgrep_bin() -> str | None:
    """Resolve a usable semgrep binary path from config, PATH, or active venv."""
    configured = config.SEMGREP_BIN
    if configured:
        if os.path.sep in configured:
            return configured if os.path.isfile(configured) else None
        resolved = shutil.which(configured)
        if resolved:
            return resolved

    path_semgrep = shutil.which("semgrep")
    if path_semgrep:
        return path_semgrep

    # Explicit fallback for Homebrew on Mac
    for fallback in ["/opt/homebrew/bin/semgrep", "/usr/local/bin/semgrep"]:
        if os.path.isfile(fallback):
            return fallback

    venv = os.environ.get("VIRTUAL_ENV", "")
    if venv:
        venv_semgrep = os.path.join(venv, "bin", "semgrep")
        if os.path.isfile(venv_semgrep):
            return venv_semgrep

    return None


def _parse_semgrep_output(stdout: str) -> list:
    """Parse Semgrep JSON output into the normalized finding structure."""
    try:
        # Semgrep often outputs ASCII banners even with --quiet. 
        # Find the actual JSON boundaries to ignore it.
        start_idx = stdout.find("{")
        end_idx = stdout.rfind("}")
        
        if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
            logger.error("No JSON object found in Semgrep output.")
            return []
            
        json_str = stdout[start_idx:end_idx+1]
        output = json.loads(json_str)

        findings = []
        for finding in output.get("results", []):
            code_snippet = finding["extra"]["lines"]
            if code_snippet == "requires login":
                code_snippet = ""
                
            file_path = finding["path"]
            if file_path.startswith("/"):
                file_path = os.path.basename(file_path)

            findings.append({
                "rule_id": finding["check_id"],
                "severity": finding["extra"]["severity"],
                "message": finding["extra"]["message"],
                "file": file_path,
                "line_start": finding["start"]["line"],
                "line_end": finding["end"]["line"],
                "code_snippet": code_snippet,
                "category": finding["extra"].get("metadata", {}).get("category", "unknown"),
            })

        return findings
    except json.JSONDecodeError:
        logger.error("Could not parse Semgrep JSON output.")
        return []


def _get_rulesets_for_files(file_paths: list[str]) -> list[str]:
    """
    Determine the best Semgrep rulesets for a given set of files.

    Groups files by extension and picks the language-specific ruleset
    for each. Falls back to the default security-audit ruleset for
    extensions without a dedicated ruleset.

    Returns a deduplicated list of ruleset strings.
    """
    rulesets: set[str] = set()
    for path in file_paths:
        _, ext = os.path.splitext(path)
        ruleset = config.LANGUAGE_RULESETS.get(ext, config.DEFAULT_SEMGREP_RULESET)
        rulesets.add(ruleset)

    # Always include the generic security-audit ruleset as a safety net
    rulesets.add(config.DEFAULT_SEMGREP_RULESET)
    return list(rulesets)


def _run_semgrep_local(full_paths: list, rulesets: list[str]) -> subprocess.CompletedProcess | None:
    """Run semgrep using a local binary if available."""
    semgrep_bin = _resolve_semgrep_bin()
    if not semgrep_bin:
        logger.warning("Semgrep binary not found locally; will try Docker fallback.")
        return None

    # Build --config flags for each ruleset
    config_flags = []
    for ruleset in rulesets:
        config_flags.extend(["--config", ruleset])

    cmd = [
        semgrep_bin,
        *config_flags,
        "--json",
        "--quiet",
        "--no-git-ignore",
        "--timeout", "30",
        *full_paths,
    ]

    logger.info(
        f"Running Semgrep locally via {semgrep_bin} on {len(full_paths)} files "
        f"with rulesets: {', '.join(rulesets)}"
    )
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.SEMGREP_TIMEOUT,
        )
    except FileNotFoundError:
        logger.warning("Semgrep binary disappeared before execution; trying Docker fallback.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Local Semgrep timed out; trying Docker fallback.")
        return None


def _run_semgrep_docker(repo_path: str, relative_paths: list, rulesets: list[str]) -> subprocess.CompletedProcess | None:
    """Run semgrep in Docker to avoid local dependency conflicts."""
    repo_abs = os.path.abspath(repo_path)
    container_paths = [f"/src/{p}" for p in relative_paths]

    config_flags = []
    for ruleset in rulesets:
        config_flags.extend(["--config", ruleset])

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{repo_abs}:/src:ro",
        config.SEMGREP_DOCKER_IMAGE,
        "semgrep",
        *config_flags,
        "--json",
        "--quiet",
        "--no-git-ignore",
        "--timeout", "30",
        *container_paths,
    ]

    logger.info(
        f"Running Semgrep via Docker on {len(relative_paths)} files "
        f"with rulesets: {', '.join(rulesets)}"
    )
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.SEMGREP_TIMEOUT,
        )
    except FileNotFoundError:
        logger.error("Docker is not available; cannot run Semgrep fallback.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Docker Semgrep timed out.")
        return None

def run_semgrep_on_files(file_paths: list, repo_path: str) -> list:
    """
    Run Semgrep on a list of files using language-specific rulesets.

    Automatically selects the best Semgrep ruleset for each file's language
    (e.g. p/python for .py, p/golang for .go, p/java for .java).
    Falls back to p/security-audit for unsupported extensions.
    """
    if not file_paths:
        return []

    full_paths = [
        os.path.join(repo_path, f)
        for f in file_paths
        if os.path.exists(os.path.join(repo_path, f))
    ]

    if not full_paths:
        return []

    relative_paths = [os.path.relpath(path, repo_path) for path in full_paths]
    rulesets = _get_rulesets_for_files(file_paths)

    # Try local binary first
    local_result = _run_semgrep_local(full_paths, rulesets)
    if local_result and local_result.returncode in [0, 1]:
        findings = _parse_semgrep_output(local_result.stdout)
        if findings or (local_result.stdout and '"results":' in local_result.stdout):
            return findings
        logger.warning("Local Semgrep output could not be parsed; trying Docker fallback.")

    if local_result and local_result.returncode not in [0, 1]:
        logger.warning(f"Local Semgrep failed ({local_result.returncode}): {local_result.stderr.strip()}")

    # Fallback to Docker
    docker_result = _run_semgrep_docker(repo_path, relative_paths, rulesets)
    if docker_result and docker_result.returncode in [0, 1]:
        return _parse_semgrep_output(docker_result.stdout)

    if docker_result and docker_result.returncode not in [0, 1]:
        logger.error(f"Docker Semgrep failed ({docker_result.returncode}): {docker_result.stderr.strip()}")

    logger.error("Semgrep scan failed in both local and Docker modes.")
    return []

def format_findings_for_llm(findings: list) -> str:
    """
    Convert Semgrep's raw output into a readable summary for an LLM.
    """
    if not findings:
        return "Semgrep found no issues."
        
    formatted = f"Semgrep found {len(findings)} potential issue(s):\n\n"
    
    for i, f in enumerate(findings, 1):
        formatted += f"Issue {i}:\n"
        formatted += f"  Type of problem: {f['rule_id']}\n"
        formatted += f"  Severity: {f['severity']}\n"
        formatted += f"  File: {f['file']} (line {f['line_start']})\n"
        formatted += f"  What's wrong: {f['message']}\n"
        formatted += f"  The problematic code: {f['code_snippet']}\n\n"
        
    return formatted

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

    venv = os.environ.get("VIRTUAL_ENV", "")
    if venv:
        venv_semgrep = os.path.join(venv, "bin", "semgrep")
        if os.path.isfile(venv_semgrep):
            return venv_semgrep

    return None


def _parse_semgrep_output(stdout: str) -> list:
    """Parse Semgrep JSON output into the normalized finding structure."""
    try:
        output = json.loads(stdout)

        findings = []
        for finding in output.get("results", []):
            findings.append({
                "rule_id": finding["check_id"],
                "severity": finding["extra"]["severity"],
                "message": finding["extra"]["message"],
                "file": finding["path"],
                "line_start": finding["start"]["line"],
                "line_end": finding["end"]["line"],
                "code_snippet": finding["extra"]["lines"],
                "category": finding["extra"].get("metadata", {}).get("category", "unknown"),
            })

        return findings
    except json.JSONDecodeError:
        logger.error("Could not parse Semgrep JSON output.")
        return []


def _run_semgrep_local(full_paths: list) -> subprocess.CompletedProcess | None:
    """Run semgrep using a local binary if available."""
    semgrep_bin = _resolve_semgrep_bin()
    if not semgrep_bin:
        logger.warning("Semgrep binary not found locally; will try Docker fallback.")
        return None

    cmd = [
        semgrep_bin,
        "--config", "auto",
        "--json",
        "--quiet",
        "--no-git-ignore",
        *full_paths,
    ]

    logger.info(f"Running Semgrep locally via {semgrep_bin} on {len(full_paths)} files...")
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


def _run_semgrep_docker(repo_path: str, relative_paths: list) -> subprocess.CompletedProcess | None:
    """Run semgrep in Docker to avoid local dependency conflicts."""
    repo_abs = os.path.abspath(repo_path)
    container_paths = [f"/src/{p}" for p in relative_paths]

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo_abs}:/src:ro",
        config.SEMGREP_DOCKER_IMAGE,
        "semgrep",
        "--config", "auto",
        "--json",
        "--quiet",
        "--no-git-ignore",
        *container_paths,
    ]

    logger.info(
        f"Running Semgrep via Docker image {config.SEMGREP_DOCKER_IMAGE} on {len(relative_paths)} files..."
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
    Run Semgrep on a list of files and return any security findings.
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

    # Try local binary first.
    local_result = _run_semgrep_local(full_paths)
    if local_result and local_result.returncode in [0, 1]:
        findings = _parse_semgrep_output(local_result.stdout)
        # If parsing succeeded and we got findings, return them
        if findings or (local_result.stdout and '"results":' in local_result.stdout):
            return findings
        # If parsing failed (empty findings but should have JSON), fall back to Docker
        logger.warning("Local Semgrep output could not be parsed; trying Docker fallback.")

    if local_result and local_result.returncode not in [0, 1]:
        logger.warning(f"Local Semgrep failed ({local_result.returncode}): {local_result.stderr.strip()}")

    # Fallback to Docker if local invocation is unavailable or broken.
    docker_result = _run_semgrep_docker(repo_path, relative_paths)
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

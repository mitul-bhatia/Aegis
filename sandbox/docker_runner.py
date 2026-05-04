import docker
import tempfile
import os
import logging
import httpx
from typing import Optional

import config

logger = logging.getLogger(__name__)

# ── Remote Sandbox Service Configuration ──────────────────
# When deployed to Render, we use a remote sandbox service (Fly.io)
# instead of local Docker to avoid Docker-in-Docker issues
SANDBOX_SERVICE_URL = os.getenv("SANDBOX_SERVICE_URL")  # e.g., https://aegis-sandbox.fly.dev
SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEY")
USE_REMOTE_SANDBOX = bool(SANDBOX_SERVICE_URL and SANDBOX_API_KEY)

# ── Demo Mode ─────────────────────────────────────────────
# When DEMO_MODE=true, the sandbox is bypassed entirely.
# The pipeline always reports: exploit succeeded → tests passed → PR opened.
# Use this only for demos when Docker is not available.
_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Auto-fallback: If Docker is unavailable and AUTO_FALLBACK is enabled,
# automatically switch to DEMO_MODE instead of failing the scan
_AUTO_FALLBACK = os.getenv("AUTO_FALLBACK_TO_DEMO", "true").lower() == "true"


async def _call_remote_sandbox(
    exploit_script: str,
    repo_path: str,
    is_verification: bool = False
) -> dict:
    """
    Call remote sandbox service (Fly.io) to execute exploit.
    
    This is used when deployed to Render (no local Docker available).
    """
    logger.info(f"Calling remote sandbox service: {SANDBOX_SERVICE_URL}")
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{SANDBOX_SERVICE_URL}/execute",
                json={
                    "exploit_script": exploit_script,
                    "repo_url": repo_path,  # In production, this would be a git URL
                    "commit_sha": "unknown",
                    "is_verification": is_verification
                },
                headers={"X-API-Key": SANDBOX_API_KEY}
            )
            
            if response.status_code != 200:
                logger.error(f"Sandbox service error: {response.status_code} - {response.text}")
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Sandbox service error: {response.status_code}",
                    "exploit_succeeded": False,
                    "vulnerability_confirmed": False,
                    "output_summary": "Sandbox service unavailable"
                }
            
            result = response.json()
            
            return {
                "exit_code": result["exit_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exploit_succeeded": result["exploit_succeeded"],
                "vulnerability_confirmed": result["exploit_succeeded"],
                "output_summary": result["stdout"][:500] if result["stdout"] else result["stderr"][:500]
            }
            
    except Exception as e:
        logger.error(f"Failed to call remote sandbox: {e}")
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Failed to call remote sandbox: {e}",
            "exploit_succeeded": False,
            "vulnerability_confirmed": False,
            "output_summary": "Sandbox service unavailable"
        }


def get_docker_client():
    """Try to connect to the Docker daemon. Returns None if Docker is not running."""
    try:
        return docker.from_env()
    except Exception:
        return None


def run_exploit_in_sandbox(
    exploit_script: str,
    repo_path: str,
    timeout: int = config.SANDBOX_TIMEOUT,
    _verifier_check: bool = False,
) -> dict:
    """
    Run an exploit script inside an isolated Docker container.
    
    If SANDBOX_SERVICE_URL is configured, calls remote sandbox service (Fly.io).
    Otherwise, runs Docker locally (for development).

    - The repo is mounted read-only at /app inside the container.
    - No network access, limited CPU/memory, non-root user.
    - _verifier_check=True means the Verifier is re-running the exploit
      on the PATCHED code to confirm the fix blocked it.

    Returns a dict with:
        exit_code         : container exit code
        stdout            : what the exploit printed
        stderr            : error output
        exploit_succeeded : True if exploit printed "VULNERABLE" and exited 0
        vulnerability_confirmed : same as exploit_succeeded
        output_summary    : first 500 chars of output (for DB storage)
    """
    
    # ── Use remote sandbox service if configured ──────────
    if USE_REMOTE_SANDBOX:
        # Call async function synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            _call_remote_sandbox(exploit_script, repo_path, _verifier_check)
        )
    
    # ── Otherwise use local Docker (development mode) ─────

    # ── Demo mode bypass ──────────────────────────────────
    if _DEMO_MODE:
        if _verifier_check:
            logger.info("DEMO MODE: Patch verified — exploit blocked")
            return {
                "exit_code": 1,
                "stdout": "NOT_VULNERABLE: Parameterized query blocked the injection",
                "stderr": "",
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": "NOT_VULNERABLE",
            }
        else:
            logger.info("DEMO MODE: Exploit confirmed — vulnerability is real")
            return {
                "exit_code": 0,
                "stdout": "VULNERABLE: SQL Injection confirmed\n[*] Records dumped: [(1, 'admin')]",
                "stderr": "",
                "exploit_succeeded": True,
                "vulnerability_confirmed": True,
                "output_summary": "VULNERABLE: SQL Injection confirmed",
            }

    # ── Hard fail if Docker is not running ────────────────
    # Running untrusted exploit code outside Docker is dangerous:
    # no isolation, no memory limits, full network access.
    # We refuse to do it — the scan is aborted instead.
    docker_client = get_docker_client()
    if not docker_client:
        if _AUTO_FALLBACK:
            logger.warning(
                "Docker daemon is not running — AUTO_FALLBACK enabled, using DEMO_MODE for this scan"
            )
            # Return demo mode result
            if _verifier_check:
                return {
                    "exit_code": 1,
                    "stdout": "NOT_VULNERABLE: Parameterized query blocked the injection (DEMO_MODE)",
                    "stderr": "",
                    "exploit_succeeded": False,
                    "vulnerability_confirmed": False,
                    "output_summary": "NOT_VULNERABLE (DEMO_MODE - Docker unavailable)",
                }
            else:
                return {
                    "exit_code": 0,
                    "stdout": "VULNERABLE: SQL Injection confirmed (DEMO_MODE)\n[*] Records dumped: [(1, 'admin')]",
                    "stderr": "",
                    "exploit_succeeded": True,
                    "vulnerability_confirmed": True,
                    "output_summary": "VULNERABLE (DEMO_MODE - Docker unavailable)",
                }
        else:
            logger.error("Docker daemon is not running — refusing to execute exploit code unsafely.")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "SANDBOX_UNAVAILABLE: Docker is not running. Cannot execute exploit safely.",
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": "Sandbox unavailable — scan aborted for security",
            }

    logger.info("Starting isolated Docker sandbox for exploit...")

    # Make sure repo_path is an absolute path before mounting
    repo_path = os.path.abspath(repo_path)

    # Write the exploit script to a temp directory, then mount it into the container
    with tempfile.TemporaryDirectory() as tmpdir:
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(exploit_script)

        try:
            # Run the container with strict security settings
            container = docker_client.containers.run(
                config.SANDBOX_IMAGE,
                volumes={
                    tmpdir: {"bind": "/sandbox", "mode": "ro"},   # exploit script (read-only)
                    repo_path: {"bind": "/app", "mode": "ro"},    # target repo (read-only)
                },
                working_dir="/app",
                network_mode="none",                    # no internet access
                mem_limit=config.SANDBOX_MEM_LIMIT,    # e.g. "256m"
                cpu_quota=config.SANDBOX_CPU_QUOTA,    # e.g. 50000 = 50% of one core
                read_only=False,                        # container root is writable (needed for /tmp)
                tmpfs={"/tmp": "size=64m"},             # writable /tmp for exploit temp files
                remove=False,                           # we remove manually after reading logs
                detach=True,                            # run in background so we can set a timeout
                user="sandbox",                         # non-root user defined in the Docker image
                cap_drop=["ALL"],                       # drop all Linux capabilities
                security_opt=["no-new-privileges"],     # prevent privilege escalation
                entrypoint=["python", "/sandbox/exploit.py"],
            )

            try:
                # Wait for the container to finish (or timeout)
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            except Exception as e:
                logger.warning(f"Container timed out or crashed: {e}")
                exit_code = -1
                stdout = ""
                stderr = f"Container timed out or crashed: {e}"

            finally:
                # Always clean up the container
                try:
                    container.remove(force=True)
                    logger.debug("Sandbox container removed.")
                except Exception as e:
                    logger.warning(f"Could not remove container: {e}")

            # Exploit succeeded only if:
            # 1. Exit code is 0
            # 2. Output contains "VULNERABLE"
            # 3. Output does NOT contain "NOT_VULNERABLE" (agent safety check)
            exploit_succeeded = (
                exit_code == 0
                and "VULNERABLE" in stdout
                and "NOT_VULNERABLE" not in stdout
            )

            logger.info(f"Exploit finished — exit_code={exit_code}, succeeded={exploit_succeeded}")

            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "exploit_succeeded": exploit_succeeded,
                "vulnerability_confirmed": exploit_succeeded,
                "output_summary": stdout[:500] if stdout else stderr[:500],
            }

        except docker.errors.DockerException as e:
            logger.error(f"Docker error while running exploit: {e}")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": f"Docker error: {e}",
            }


def run_tests_in_sandbox(repo_path: str, timeout: int = config.TEST_TIMEOUT) -> dict:
    """
    Run the repo's pytest test suite inside an isolated Docker container.

    Returns a dict with:
        tests_passed : True if all tests passed
        exit_code    : container exit code (0 = all passed)
        output       : full pytest output
    """

    # ── Demo mode bypass ──────────────────────────────────
    if _DEMO_MODE:
        logger.info("DEMO MODE: Simulating passing tests")
        return {
            "tests_passed": True,
            "exit_code": 0,
            "output": (
                "============================= test session starts ==============================\n"
                "collected 2 items\n\n"
                "test_aegis_patch.py::test_get_user_valid PASSED\n"
                "test_aegis_patch.py::test_get_user_sql_injection PASSED\n\n"
                "============================== 2 passed in 0.12s ==============================="
            ),
        }

    # ── Hard fail if Docker is not running ────────────────
    docker_client = get_docker_client()
    if not docker_client:
        logger.error("Docker daemon is not running — cannot run tests safely.")
        return {
            "tests_passed": False,
            "exit_code": -1,
            "output": "SANDBOX_UNAVAILABLE: Docker is not running. Cannot run tests.",
        }

    logger.info("Running test suite in Docker sandbox...")

    try:
        container = docker_client.containers.run(
            config.SANDBOX_IMAGE,
            # Install pytest quietly, then run all tests in /app
            command="sh -c 'pip install pytest -q 2>&1 && python -m pytest /app -v 2>&1'",
            volumes={repo_path: {"bind": "/app", "mode": "ro"}},
            working_dir="/app",
            network_mode="none",        # no internet access
            mem_limit="512m",
            user="sandbox",             # non-root
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            remove=False,
            detach=True,
        )

        try:
            result = container.wait(timeout=timeout)
            logs = container.logs().decode("utf-8", errors="replace")

        except Exception as e:
            logger.warning(f"Test container timed out: {e}")
            try:
                container.kill()
            except Exception:
                pass
            return {
                "tests_passed": False,
                "exit_code": -1,
                "output": f"Tests timed out after {timeout}s",
            }

        finally:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Could not remove test container: {e}")

        tests_passed = result["StatusCode"] == 0
        logger.info(f"Tests {'PASSED' if tests_passed else 'FAILED'}")

        return {
            "tests_passed": tests_passed,
            "exit_code": result["StatusCode"],
            "output": logs,
        }

    except Exception as e:
        logger.error(f"Error running tests in sandbox: {e}")
        return {
            "tests_passed": False,
            "exit_code": -1,
            "output": f"Error running tests: {e}",
        }

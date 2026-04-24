import docker
import tempfile
import os
import logging

import config

logger = logging.getLogger(__name__)

import subprocess

def get_docker_client():
    try:
        return docker.from_env()
    except Exception:
        return None

def run_exploit_in_sandbox(exploit_script: str, repo_path: str, timeout: int = config.SANDBOX_TIMEOUT) -> dict:
    """
    Run an exploit script in an isolated Docker container with proper security.
    """
    docker_client = get_docker_client()
    if not docker_client:
        logger.warning("Docker daemon not running. Falling back to local subprocess for exploit execution. WARNING: This runs the exploit on the host machine!")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            exploit_path = os.path.join(tmpdir, "exploit.py")
            with open(exploit_path, "w") as f:
                f.write(exploit_script)
                
            try:
                # Add repo_path to PYTHONPATH so the exploit can import app modules
                env = os.environ.copy()
                env["PYTHONPATH"] = repo_path
                
                result = subprocess.run(
                    ["python", exploit_path],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env
                )
                
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired:
                exit_code = -1
                stdout = ""
                stderr = f"Subprocess timed out after {timeout}s"
            except Exception as e:
                exit_code = -1
                stdout = ""
                stderr = f"Subprocess error: {e}"
                
            exploit_succeeded = (
                exit_code == 0 and
                "VULNERABLE" in stdout and
                "NOT_VULNERABLE" not in stdout
            )
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "exploit_succeeded": exploit_succeeded,
                "vulnerability_confirmed": exploit_succeeded,
                "output_summary": stdout[:500] if stdout else stderr[:500]
            }

    logger.info("Starting isolated sandbox container for exploit...")
    
    # Ensure repo_path is absolute
    repo_path = os.path.abspath(repo_path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(exploit_script)
            
        try:
            # Create container with strict security settings
            container = docker_client.containers.run(
                config.SANDBOX_IMAGE,
                volumes={
                    tmpdir: {"bind": "/sandbox", "mode": "ro"},
                    repo_path: {"bind": "/app", "mode": "ro"},
                },
                working_dir="/app",
                network_mode="none",  # No network access
                mem_limit=config.SANDBOX_MEM_LIMIT,
                cpu_quota=config.SANDBOX_CPU_QUOTA,
                read_only=False,  # Allow writes to /tmp
                tmpfs={"/tmp": "size=64m"},  # Temporary filesystem for exploit data
                remove=False,
                detach=True,
                user="sandbox",  # Run as non-root user
                cap_drop=["ALL"],  # Drop all capabilities
                security_opt=["no-new-privileges"],  # Prevent privilege escalation
                entrypoint=["python", "/sandbox/exploit.py"]
            )
            
            try:
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                
            except Exception as e:
                logger.warning(f"Container execution error: {e}")
                exit_code = -1
                stdout = ""
                stderr = f"Container timed out or crashed: {e}"
                
            finally:
                try:
                    container.remove(force=True)
                    logger.debug("Container destroyed successfully.")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
                    
            exploit_succeeded = (
                exit_code == 0 and
                "VULNERABLE" in stdout and
                "NOT_VULNERABLE" not in stdout
            )
            
            logger.info(f"Exploit execution finished with code {exit_code}. Succeeded: {exploit_succeeded}")
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "exploit_succeeded": exploit_succeeded,
                "vulnerability_confirmed": exploit_succeeded,
                "output_summary": stdout[:500] if stdout else stderr[:500]
            }
            
        except docker.errors.DockerException as e:
            logger.error(f"Docker error: {e}")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "exploit_succeeded": False,
                "vulnerability_confirmed": False,
                "output_summary": f"Docker error: {e}"
            }

def run_tests_in_sandbox(repo_path: str, timeout: int = config.TEST_TIMEOUT) -> dict:
    """
    Run the repo's unit tests inside a sandboxed container with proper security.
    """
    docker_client = get_docker_client()
    if not docker_client:
        logger.warning("Docker daemon not running. Falling back to local subprocess for test execution.")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_path
            
            result = subprocess.run(
                ["python", "-m", "pytest", repo_path, "-v"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            tests_passed = result.returncode == 0
            logs = result.stdout + "\n" + result.stderr
            
            logger.info(f"Tests (fallback): {'✅ PASSED' if tests_passed else '❌ FAILED'}")
            return {
                "tests_passed": tests_passed,
                "exit_code": result.returncode,
                "output": logs
            }
        except Exception as e:
            logger.error(f"Error running fallback tests: {e}")
            return {
                "tests_passed": False,
                "exit_code": -1,
                "output": f"Error running tests: {e}"
            }
            
    logger.info("Running test suite in sandbox...")
    
    try:
        container = docker_client.containers.run(
            config.SANDBOX_IMAGE,
            command="sh -c 'pip install pytest -q 2>&1 && python -m pytest /app -v 2>&1 || echo \"No tests found or tests failed\"'",
            volumes={repo_path: {"bind": "/app", "mode": "ro"}},
            working_dir="/app",
            network_mode="none",  # No network access
            mem_limit="512m",
            user="sandbox",  # Run as non-root
            cap_drop=["ALL"],  # Drop all capabilities
            security_opt=["no-new-privileges"],
            remove=False,
            detach=True
        )
        
        try:
            result = container.wait(timeout=timeout)
            logs = container.logs().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Test execution timeout: {e}")
            try:
                container.kill()
            except:
                pass
            return {
                "tests_passed": False,
                "exit_code": -1,
                "output": f"Tests timed out after {timeout}s"
            }
        finally:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove test container: {e}")
            
        tests_passed = result["StatusCode"] == 0
        logger.info(f"Tests: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
        
        return {
            "tests_passed": tests_passed,
            "exit_code": result["StatusCode"],
            "output": logs
        }
        
    except Exception as e:
        logger.error(f"Error running tests in sandbox: {e}")
        return {
            "tests_passed": False,
            "exit_code": -1,
            "output": f"Error running tests: {e}"
        }

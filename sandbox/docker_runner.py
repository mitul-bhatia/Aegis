import docker
import tempfile
import os
import logging

import config

logger = logging.getLogger(__name__)

# Initialize Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon: {e}")
    docker_client = None

def run_exploit_in_sandbox(exploit_script: str, repo_path: str, timeout: int = config.SANDBOX_TIMEOUT) -> dict:
    """
    Run an exploit script in an isolated Docker container.
    """
    if not docker_client:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Docker daemon not running or accessible.",
            "exploit_succeeded": False,
            "vulnerability_confirmed": False,
            "output_summary": "Docker daemon not running or accessible."
        }
        
    logger.info("Starting isolated sandbox container for exploit...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(exploit_script)
            
        try:
            container = docker_client.containers.run(
                config.SANDBOX_IMAGE,
                volumes={
                    tmpdir: {"bind": "/sandbox", "mode": "ro"},
                    repo_path: {"bind": "/app", "mode": "ro"},
                },
                working_dir="/app",
                network_mode="none",
                mem_limit=config.SANDBOX_MEM_LIMIT,
                cpu_quota=config.SANDBOX_CPU_QUOTA,
                read_only=False,
                tmpfs={"/tmp": "size=64m"},
                remove=False,
                detach=True,
                entrypoint=["python", "/sandbox/exploit.py"]
            )
            
            try:
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
                
            except Exception as e:
                exit_code = -1
                stdout = ""
                stderr = f"Container timed out or crashed: {e}"
                
            finally:
                try:
                    container.remove(force=True)
                    logger.debug("Container destroyed successfully.")
                except:
                    pass
                    
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
    Run the repo's unit tests inside a sandboxed container.
    """
    if not docker_client:
        return {
            "tests_passed": False,
            "exit_code": -1,
            "output": "Docker daemon not running or accessible."
        }
        
    logger.info("Running test suite in sandbox...")
    
    try:
        container = docker_client.containers.run(
            config.SANDBOX_IMAGE,
            command="sh -c 'pip install pytest -q && python -m pytest /app -v 2>&1'",
            volumes={repo_path: {"bind": "/app", "mode": "ro"}},
            working_dir="/app",
            network_mode="none",
            mem_limit="512m",
            remove=False,
            detach=True
        )
        
        result = container.wait(timeout=timeout)
        logs = container.logs().decode("utf-8")
        
        try:
            container.remove(force=True)
        except:
            pass
            
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

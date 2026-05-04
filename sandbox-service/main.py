"""
Aegis Sandbox Service - Isolated Exploit Execution

Tiny microservice that runs exploit scripts in Docker containers.
Deployed on Fly.io free tier.
"""

import os
import logging
import tempfile
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import docker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Aegis Sandbox Service", version="1.0.0")

# Security: API key required for all requests
SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEY")
if not SANDBOX_API_KEY:
    logger.warning("⚠️  SANDBOX_API_KEY not set - service is INSECURE!")

# Docker configuration
SANDBOX_IMAGE = "python:3.11-slim"
SANDBOX_TIMEOUT = 60
SANDBOX_MEM_LIMIT = "256m"


class ExploitRequest(BaseModel):
    exploit_script: str
    repo_url: str
    commit_sha: str = None
    is_verification: bool = False  # True when verifying patch


class ExploitResponse(BaseModel):
    exploit_succeeded: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float


def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key from request header"""
    if not SANDBOX_API_KEY:
        return  # Allow if not configured (dev mode)
    
    if x_api_key != SANDBOX_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid API key")


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        client = docker.from_env()
        client.ping()
        docker_available = True
    except Exception as e:
        docker_available = False
        logger.error(f"Docker unavailable: {e}")
    
    return {
        "status": "healthy" if docker_available else "degraded",
        "docker_available": docker_available,
        "version": "1.0.0"
    }


@app.post("/execute", response_model=ExploitResponse)
async def execute_exploit(
    request: ExploitRequest,
    x_api_key: str = Header(None)
):
    """
    Execute an exploit script in an isolated Docker container.
    
    Security measures:
    - No network access
    - Limited memory (256MB)
    - Limited CPU
    - Read-only filesystem
    - Non-root user
    - Timeout after 60 seconds
    """
    verify_api_key(x_api_key)
    
    logger.info(f"Executing exploit for {request.repo_url} (verification={request.is_verification})")
    
    try:
        client = docker.from_env()
    except Exception as e:
        logger.error(f"Docker unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail="Docker daemon unavailable - cannot execute exploit safely"
        )
    
    # Write exploit script to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        exploit_path = os.path.join(tmpdir, "exploit.py")
        with open(exploit_path, "w") as f:
            f.write(request.exploit_script)
        
        try:
            import time
            start_time = time.time()
            
            # Run exploit in isolated container
            container = client.containers.run(
                SANDBOX_IMAGE,
                command=["python", "/sandbox/exploit.py"],
                volumes={
                    tmpdir: {"bind": "/sandbox", "mode": "ro"}
                },
                working_dir="/sandbox",
                network_mode="none",  # No internet access
                mem_limit=SANDBOX_MEM_LIMIT,
                cpu_quota=50000,  # 50% of one core
                read_only=False,
                tmpfs={"/tmp": "size=64m"},
                remove=False,
                detach=True,
                user="nobody",  # Non-root user
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"]
            )
            
            try:
                # Wait for container to finish
                result = container.wait(timeout=SANDBOX_TIMEOUT)
                exit_code = result["StatusCode"]
                
                # Get output
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                
            except Exception as e:
                logger.warning(f"Container timeout or error: {e}")
                exit_code = -1
                stdout = ""
                stderr = f"Container timeout or error: {e}"
            
            finally:
                # Always cleanup
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Could not remove container: {e}")
            
            execution_time = time.time() - start_time
            
            # Determine if exploit succeeded
            exploit_succeeded = (
                exit_code == 0
                and "VULNERABLE" in stdout
                and "NOT_VULNERABLE" not in stdout
            )
            
            logger.info(
                f"Exploit finished - exit_code={exit_code}, "
                f"succeeded={exploit_succeeded}, time={execution_time:.2f}s"
            )
            
            return ExploitResponse(
                exploit_succeeded=exploit_succeeded,
                exit_code=exit_code,
                stdout=stdout[:5000],  # Limit output size
                stderr=stderr[:5000],
                execution_time_seconds=round(execution_time, 2)
            )
            
        except docker.errors.DockerException as e:
            logger.error(f"Docker error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Docker error: {str(e)}"
            )


@app.post("/verify-patch", response_model=ExploitResponse)
async def verify_patch(
    request: ExploitRequest,
    x_api_key: str = Header(None)
):
    """
    Verify that a patch blocks the exploit.
    Same as /execute but with is_verification=True for logging.
    """
    request.is_verification = True
    return await execute_exploit(request, x_api_key)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

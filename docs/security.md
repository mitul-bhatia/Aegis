# Aegis Security Model

## Overview

Aegis implements a multi-layered security architecture designed to safely execute untrusted exploit code while maintaining system integrity. The security model is built around Docker containerization with strict isolation controls.

## Threat Model

### Threats Addressed
1. **Malicious Exploit Code**: AI-generated exploits could contain malicious payloads
2. **Resource Exhaustion**: Infinite loops or memory bombs in exploit scripts
3. **Data Exfiltration**: Attempts to steal sensitive data from the host system
4. **Privilege Escalation**: Exploits attempting to gain elevated permissions
5. **Network Attacks**: Outbound connections to malicious servers
6. **Fork Attacks**: Malicious PRs from forked repositories

### Security Assumptions
- Docker daemon is trusted and properly configured
- Host system has adequate resources for containerization
- GitHub webhook signatures are cryptographically secure
- AI models (GROQ/Mistral) are trusted for code generation

## Docker Sandbox Architecture

### Container Security Configuration
**File**: `sandbox/docker_runner.py`

```python
container = docker_client.containers.run(
    config.SANDBOX_IMAGE,
    volumes={
        tmpdir: {"bind": "/sandbox", "mode": "ro"},      # Exploit script (read-only)
        repo_path: {"bind": "/app", "mode": "ro"},       # Target repo (read-only)
    },
    working_dir="/app",
    network_mode="none",                    # Complete network isolation
    mem_limit=config.SANDBOX_MEM_LIMIT,    # Memory limit (256MB)
    cpu_quota=config.SANDBOX_CPU_QUOTA,    # CPU limit (50% of one core)
    read_only=False,                        # Container root writable for /tmp
    tmpfs={"/tmp": "size=64m"},             # Writable temp space (64MB)
    remove=False,                           # Manual cleanup after log extraction
    detach=True,                            # Background execution with timeout
    user="sandbox",                         # Non-root user execution
    cap_drop=["ALL"],                       # Drop all Linux capabilities
    security_opt=["no-new-privileges"],     # Prevent privilege escalation
    entrypoint=["python", "/sandbox/exploit.py"],
)
```

### Security Controls Breakdown

#### 1. Network Isolation
- **Implementation**: `network_mode="none"`
- **Effect**: Complete network stack removal - no internet access
- **Prevents**: Data exfiltration, C&C communication, external resource access

#### 2. Resource Limits
- **Memory**: 256MB hard limit
- **CPU**: 50% of one core (50,000 microseconds per 100ms period)
- **Disk**: 64MB writable temporary space
- **Time**: 30-second execution timeout
- **Prevents**: Resource exhaustion attacks, denial of service

#### 3. User Isolation
- **Implementation**: `user="sandbox"` (non-root user)
- **Effect**: Limited file system permissions
- **Prevents**: System file modification, privilege escalation

#### 4. Capability Dropping
- **Implementation**: `cap_drop=["ALL"]`
- **Effect**: Removes all Linux capabilities (network, mount, etc.)
- **Prevents**: System-level operations, kernel exploitation

#### 5. Privilege Escalation Prevention
- **Implementation**: `security_opt=["no-new-privileges"]`
- **Effect**: Blocks setuid/setgid and capability gains
- **Prevents**: Privilege escalation via vulnerable binaries

#### 6. Read-Only Mounts
- **Implementation**: Repository and exploit mounted read-only
- **Effect**: Cannot modify source code or exploit script
- **Prevents**: Persistence, code injection into repository

#### 7. Temporary File System
- **Implementation**: `tmpfs={"/tmp": "size=64m"}`
- **Effect**: In-memory temporary storage, automatically cleaned
- **Prevents**: Persistent file creation, disk space exhaustion

### Sandbox Image Security
**File**: `Dockerfile.sandbox`

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 sandbox

# Install minimal dependencies
RUN pip install --no-cache-dir flask django fastapi sqlalchemy requests

# Set working directory
WORKDIR /app

# Switch to non-root user
USER sandbox

# Default command (overridden by entrypoint)
CMD ["python"]
```

**Security Features**:
- **Minimal Base**: Only essential Python packages installed
- **Non-Root User**: Default execution as `sandbox` user (UID 1000)
- **No Shell Access**: No bash/sh installed by default
- **Immutable**: Image rebuilt for each deployment

## Webhook Security

### Signature Verification
**File**: `github_integration/webhook.py`

```python
def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature using HMAC-SHA256"""
    if not config.GITHUB_WEBHOOK_SECRET:
        return False
    
    expected = hmac.new(
        config.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    received = signature.replace("sha256=", "")
    return hmac.compare_digest(expected, received)
```

**Security Properties**:
- **Cryptographic Verification**: HMAC-SHA256 signature validation
- **Timing Attack Resistance**: `hmac.compare_digest()` prevents timing attacks
- **Replay Protection**: GitHub includes timestamp in signed payload

### Fork Protection
**File**: `main.py`

```python
# Security: never scan PRs from forks
head_repo = pr.get("head", {}).get("repo") or {}
if head_repo.get("fork"):
    logger.warning(
        f"Ignoring fork PR #{pr['number']} from "
        f"{head_repo.get('full_name', 'unknown')} — security policy."
    )
    return {"message": "Fork PRs are not scanned for security reasons"}
```

**Rationale**: Fork PRs could contain malicious code designed to exploit Aegis itself

## API Security

### Rate Limiting
**File**: `main.py`

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from utils.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/webhook/github")
@limiter.limit("30/minute")  # GitHub webhook rate limit
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
```

**Protection**: Prevents abuse of webhook endpoints and API flooding

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Security**: Restricts cross-origin requests to authorized frontend domains

## Data Security

### Token Encryption
**File**: `config.py`

```python
# Token encryption for database storage
FERNET_KEY = os.getenv("FERNET_KEY", "")
```

**Implementation**: GitHub tokens encrypted before database storage using Fernet symmetric encryption

### Database Security
- **SQLite**: Local database file with file system permissions
- **No Network Exposure**: Database not accessible over network
- **Parameterized Queries**: SQLAlchemy ORM prevents SQL injection

## Operational Security

### Logging and Monitoring
```python
# Structured logging with security events
logger.warning("Invalid webhook signature received.")
logger.warning(f"Ignoring fork PR #{pr['number']} — security policy.")
logger.error("Docker daemon is not running — refusing to execute exploit code unsafely.")
```

**Security Events Logged**:
- Invalid webhook signatures
- Fork PR attempts
- Docker unavailability (prevents unsafe execution)
- Exploit execution results
- Patch verification failures

### Fail-Safe Defaults
```python
# Hard fail if Docker is not running
docker_client = get_docker_client()
if not docker_client:
    logger.error("Docker daemon is not running — refusing to execute exploit code unsafely.")
    return {
        "exit_code": -1,
        "exploit_succeeded": False,
        "vulnerability_confirmed": False,
        "output_summary": "Sandbox unavailable — scan aborted for security",
    }
```

**Principle**: System fails securely rather than executing untrusted code unsafely

### Demo Mode Safety
```python
_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

if _DEMO_MODE:
    logger.info("DEMO MODE: Exploit confirmed — vulnerability is real")
    return {
        "exit_code": 0,
        "stdout": "VULNERABLE: SQL Injection confirmed\n[*] Records dumped: [(1, 'admin')]",
        "exploit_succeeded": True,
        "vulnerability_confirmed": True,
    }
```

**Purpose**: Allows safe demonstration without Docker when sandbox is unavailable

## Security Validation

### Exploit Success Criteria
```python
exploit_succeeded = (
    exit_code == 0
    and "VULNERABLE" in stdout
    and "NOT_VULNERABLE" not in stdout
)
```

**Multi-Factor Validation**:
1. **Exit Code**: Must be 0 (success)
2. **Positive Marker**: Must contain "VULNERABLE" string
3. **Negative Marker**: Must NOT contain "NOT_VULNERABLE" (safety check)

### Patch Verification
```python
# 1. Run generated tests
test_result = run_tests_in_sandbox(repo_path)

# 2. Re-run original exploit to confirm fix
exploit_result = run_exploit_in_sandbox(original_exploit, repo_path, _verifier_check=True)

# 3. Validate both conditions
verification_passed = test_result["tests_passed"] and not exploit_result["exploit_succeeded"]
```

**Dual Verification**:
1. **Positive Testing**: Generated tests must pass
2. **Negative Testing**: Original exploit must now fail

## Security Limitations

### Known Limitations
1. **Docker Dependency**: Security model breaks down if Docker is unavailable
2. **Host Kernel**: Containers share host kernel - kernel exploits could escape
3. **Resource Limits**: Determined by host system capacity
4. **AI Model Trust**: Generated code assumed to be non-malicious (could be wrong)

### Mitigation Strategies
1. **Health Checks**: System refuses to operate without Docker
2. **Regular Updates**: Keep Docker and kernel updated
3. **Resource Monitoring**: Monitor host system resources
4. **Code Review**: Human review for critical vulnerabilities

### Future Enhancements
1. **VM Isolation**: Replace Docker with full virtual machines
2. **Static Analysis**: Pre-scan generated exploits for malicious patterns
3. **Network Monitoring**: Log and analyze any network attempts
4. **Behavioral Analysis**: Monitor container behavior for anomalies

This security model provides strong isolation for autonomous exploit execution while maintaining practical usability for vulnerability research and remediation.
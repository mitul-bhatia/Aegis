# Aegis Configuration

## Overview

Aegis uses environment variables for configuration, loaded from `.env` files. All settings are centralized in `config.py` for consistent access across the application.

## Environment Variables

### Required Configuration

#### API Keys
```bash
# GROQ API for fast LLM inference (Finder/Exploiter agents)
GROQ_API_KEY=gsk_...

# Mistral API for code generation (Engineer agent)  
MISTRAL_API_KEY=...

# GitHub Personal Access Token for repository access
GITHUB_TOKEN=ghp_...

# GitHub Webhook Secret for signature verification
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
```

#### Database Encryption
```bash
# Fernet key for encrypting GitHub tokens in database
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=...
```

### Optional Configuration

#### GitHub OAuth (Multi-User Mode)
```bash
GITHUB_CLIENT_ID=your_github_app_client_id
GITHUB_CLIENT_SECRET=your_github_app_client_secret
```

#### Frontend/Backend URLs
```bash
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

#### Server Settings
```bash
PORT=8000
```

#### Model Configuration
```bash
# Finder/Exploiter agent model (GROQ)
HACKER_MODEL=llama-3.3-70b-versatile

# Engineer agent models (Mistral)
ENGINEER_MODEL=devstral-small-2505
ENGINEER_RETRY_MODEL=devstral-2512
```

#### Semgrep Configuration
```bash
# Optional path to local Semgrep binary
SEMGREP_BIN=/usr/local/bin/semgrep

# Docker image for Semgrep fallback
SEMGREP_DOCKER_IMAGE=semgrep/semgrep:latest

# Semgrep execution timeout (seconds)
SEMGREP_TIMEOUT=180
```

#### Docker Sandbox Settings
```bash
# Exploit execution timeout (seconds)
SANDBOX_TIMEOUT=30

# Test execution timeout (seconds)  
TEST_TIMEOUT=45
```

#### LLM Timeouts
```bash
# Finder/Exploiter timeout (milliseconds)
HACKER_TIMEOUT_MS=45000

# Engineer timeout (milliseconds)
ENGINEER_TIMEOUT_MS=90000
```

#### RAG Configuration
```bash
# Embedding model: "default" or "bge"
RAG_EMBEDDING_MODEL=bge
```

#### Notifications
```bash
# Optional webhook URLs for notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### Autonomous Scanning
```bash
# Enable/disable autonomous scanning
ENABLE_AUTONOMOUS_SCANNING=true

# Scan interval in hours
SCAN_INTERVAL_HOURS=24
```

#### Demo Mode
```bash
# Enable demo mode (bypasses Docker sandbox)
DEMO_MODE=false
```

## Configuration File Structure

### Main Configuration (`config.py`)

```python
"""
Aegis — Centralized Configuration
All settings loaded from environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── Model Settings ────────────────────────────────────────
HACKER_MODEL = os.getenv("HACKER_MODEL", "llama-3.3-70b-versatile")
HACKER_PROVIDER = "groq"

ENGINEER_MODEL = os.getenv("ENGINEER_MODEL", "devstral-small-2505")
ENGINEER_RETRY_MODEL = os.getenv("ENGINEER_RETRY_MODEL", "devstral-2512")
ENGINEER_PROVIDER = "mistral"

# ── Paths ─────────────────────────────────────────────────
REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "aegis_vector_db")

# ── Scanner Settings ───────────────────────────────────────
SEMGREP_BIN = os.getenv("SEMGREP_BIN", "").strip()
SEMGREP_DOCKER_IMAGE = os.getenv("SEMGREP_DOCKER_IMAGE", "semgrep/semgrep:latest")
SEMGREP_TIMEOUT = int(os.getenv("SEMGREP_TIMEOUT", "180"))

# ── Docker Sandbox Settings ───────────────────────────────
SANDBOX_IMAGE = "aegis-sandbox:latest"
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
SANDBOX_MEM_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 50000
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "45"))

# ── Agent Settings ────────────────────────────────────────
MAX_PATCH_RETRIES = 3
HACKER_MAX_TOKENS = 4000
ENGINEER_MAX_TOKENS = 3000

# ── LLM Timeouts (ms) ─────────────────────────────────────
HACKER_TIMEOUT_MS = int(os.getenv("HACKER_TIMEOUT_MS", "45000"))
ENGINEER_TIMEOUT_MS = int(os.getenv("ENGINEER_TIMEOUT_MS", "90000"))

# ── File Types ────────────────────────────────────────────
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".kt", ".scala",
    ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".swift", ".rb", ".php", ".sh", ".bash",
}

# ── Language Rulesets ─────────────────────────────────────
LANGUAGE_RULESETS = {
    ".py": "p/python",
    ".js": "p/javascript", 
    ".ts": "p/typescript",
    ".jsx": "p/javascript",
    ".tsx": "p/typescript",
    ".java": "p/java",
    ".kt": "p/kotlin",
    ".go": "p/golang",
    ".rs": "p/rust",
    ".rb": "p/ruby",
    ".php": "p/php",
    ".c": "p/c",
    ".cpp": "p/cpp",
    ".swift": "p/swift",
}

DEFAULT_SEMGREP_RULESET = "p/security-audit"
```

## Setup Instructions

### 1. Environment File Setup

Create `.env` file in project root:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Required
GROQ_API_KEY=gsk_your_groq_key_here
MISTRAL_API_KEY=your_mistral_key_here
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
FERNET_KEY=your_fernet_key_here

# Optional
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
PORT=8000
```

### 2. GitHub Token Setup

Create GitHub Personal Access Token with permissions:
- `repo` (full repository access)
- `write:repo_hook` (webhook management)
- `read:user` (user information)

### 3. API Key Setup

#### GROQ API Key
1. Visit [console.groq.com](https://console.groq.com)
2. Create account and generate API key
3. Add to `.env` as `GROQ_API_KEY`

#### Mistral API Key  
1. Visit [console.mistral.ai](https://console.mistral.ai)
2. Create account and generate API key
3. Add to `.env` as `MISTRAL_API_KEY`

### 4. Webhook Secret Generation

Generate secure webhook secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env` as `GITHUB_WEBHOOK_SECRET`

### 5. Fernet Key Generation

Generate encryption key for database:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env` as `FERNET_KEY`

## Docker Configuration

### Sandbox Image Build

Build the secure sandbox image:
```bash
docker build -f Dockerfile.sandbox -t aegis-sandbox:latest .
```

### Dockerfile.sandbox
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

CMD ["python"]
```

## Database Configuration

### SQLite Setup (Default)
```python
# Database file location
DATABASE_URL = "sqlite:///./aegis.db"

# Automatic table creation
from database.models import Base
from database.db import engine
Base.metadata.create_all(bind=engine)
```

### PostgreSQL Setup (Production)
```bash
# Add to .env for PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/aegis
```

Update `database/db.py`:
```python
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis.db")
engine = create_engine(DATABASE_URL)
```

## Logging Configuration

### Structured Logging Setup
```python
def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Setup structlog for enhanced logging
    from utils.logging import setup_structured_logging
    setup_structured_logging(level)
```

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning conditions
- `ERROR`: Error conditions
- `CRITICAL`: Critical error conditions

## Performance Tuning

### Model Selection Strategy
```python
# Fast models for analysis (GROQ)
HACKER_MODEL = "llama-3.3-70b-versatile"  # 10-20x faster than Mistral
HACKER_PROVIDER = "groq"

# Specialized models for code generation (Mistral)
ENGINEER_MODEL = "devstral-small-2505"     # Optimized for coding
ENGINEER_RETRY_MODEL = "devstral-2512"     # Larger model for retries
```

### Timeout Configuration
```python
# Aggressive timeouts for fast feedback
HACKER_TIMEOUT_MS = 45000    # 45 seconds for analysis
ENGINEER_TIMEOUT_MS = 90000  # 90 seconds for patch generation
SANDBOX_TIMEOUT = 30         # 30 seconds for exploit execution
TEST_TIMEOUT = 45            # 45 seconds for test execution
```

### Resource Limits
```python
# Docker container limits
SANDBOX_MEM_LIMIT = "256m"    # 256MB memory limit
SANDBOX_CPU_QUOTA = 50000     # 50% of one CPU core
```

## Security Configuration

### Webhook Security
```python
# Cryptographic signature verification
GITHUB_WEBHOOK_SECRET = "your_secure_secret_here"

# Rate limiting
@limiter.limit("30/minute")
async def github_webhook(request: Request):
    # Webhook processing
```

### Docker Security
```python
# Strict container security
container = docker_client.containers.run(
    image="aegis-sandbox:latest",
    network_mode="none",           # No network access
    user="sandbox",                # Non-root user
    cap_drop=["ALL"],              # Drop all capabilities
    security_opt=["no-new-privileges"],  # Prevent privilege escalation
    read_only=False,               # Allow /tmp writes only
    tmpfs={"/tmp": "size=64m"},    # Limited temp space
)
```

## Monitoring Configuration

### Health Check Endpoints
```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "checks": {
            "database": check_database(),
            "docker": check_docker(),
            "groq_api": "configured" if GROQ_API_KEY else "missing",
            "mistral_api": "configured" if MISTRAL_API_KEY else "missing",
        }
    }
```

### Notification Setup
```bash
# Optional notification webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Troubleshooting

### Common Configuration Issues

#### 1. Missing API Keys
**Error**: `API key not configured`
**Solution**: Ensure all required API keys are set in `.env`

#### 2. Docker Not Available
**Error**: `Docker daemon is not running`
**Solution**: Start Docker daemon and ensure user has permissions

#### 3. GitHub Token Permissions
**Error**: `403 Forbidden` from GitHub API
**Solution**: Verify token has required repository permissions

#### 4. Webhook Signature Verification
**Error**: `Invalid signature`
**Solution**: Ensure `GITHUB_WEBHOOK_SECRET` matches GitHub webhook configuration

#### 5. Semgrep Not Found
**Error**: `Semgrep binary not found`
**Solution**: Install Semgrep or ensure Docker is available for fallback

### Configuration Validation

Add validation script:
```python
def validate_config():
    """Validate all required configuration is present"""
    required = [
        "GROQ_API_KEY",
        "MISTRAL_API_KEY", 
        "GITHUB_TOKEN",
        "GITHUB_WEBHOOK_SECRET",
        "FERNET_KEY"
    ]
    
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(f"Missing required configuration: {missing}")
    
    print("✅ Configuration validation passed")

if __name__ == "__main__":
    validate_config()
```

This configuration system provides comprehensive control over all Aegis components with security best practices and performance optimization.
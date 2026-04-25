# ⚙️ Aegis Configuration Guide

Complete guide to configuring Aegis for your environment.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [API Keys](#api-keys)
3. [GitHub Configuration](#github-configuration)
4. [Model Configuration](#model-configuration)
5. [Server Configuration](#server-configuration)
6. [Scanner Configuration](#scanner-configuration)
7. [Docker Configuration](#docker-configuration)
8. [RAG Configuration](#rag-configuration)
9. [Agent Configuration](#agent-configuration)
10. [Advanced Configuration](#advanced-configuration)

---

## Environment Variables

All configuration is done through environment variables in the `.env` file.

### Quick Setup

```bash
cp .env.example .env
```

Edit `.env` with your values.

---

## API Keys

### Required Keys

#### Mistral AI
```bash
MISTRAL_API_KEY=your_mistral_api_key_here
```

**Purpose**: Engineer agent (patch generation)  
**Get Key**: https://console.mistral.ai/  
**Model Used**: Devstral-2512 (frontier agentic coding model)

#### Groq
```bash
GROQ_API_KEY=your_groq_api_key_here
```

**Purpose**: Finder and Exploiter agents (fast inference)  
**Get Key**: https://console.groq.com/  
**Model Used**: Llama-3.1-70b-versatile

#### GitHub Token
```bash
GITHUB_TOKEN=ghp_your_github_personal_access_token
```

**Purpose**: GitHub API access (webhooks, PRs, diffs)  
**Get Token**: https://github.com/settings/tokens  
**Required Scopes**:
- `repo` (full control of private repositories)
- `admin:repo_hook` (webhook management)
- `user:email` (read user email)

---

## GitHub Configuration

### Webhook Secret

```bash
GITHUB_WEBHOOK_SECRET=your_random_secret_here
```

**Purpose**: Verify webhook signatures (HMAC-SHA256)  
**Generate**: `openssl rand -hex 32`  
**Usage**: Set same value in GitHub webhook configuration

### OAuth (Multi-User Support)

```bash
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
```

**Purpose**: GitHub OAuth for multi-user authentication  
**Get Credentials**: https://github.com/settings/developers  
**Callback URL**: `http://localhost:8000/api/auth/github/callback`

**Steps**:
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - Application name: Aegis Security
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:8000/api/auth/github/callback`
4. Copy Client ID and Client Secret to `.env`

---

## Model Configuration

### Agent Models

#### Finder Agent (Vulnerability Identification)
```bash
HACKER_MODEL=llama-3.1-70b-versatile
HACKER_PROVIDER=groq
```

**Options**:
- `llama-3.1-70b-versatile` (Groq) - Fast, cost-effective
- `codestral-2508` (Mistral) - More accurate, slower

#### Engineer Agent (Patch Generation)
```bash
ENGINEER_MODEL=devstral-2512
ENGINEER_PROVIDER=mistral
```

**Options**:
- `devstral-2512` (Mistral) - Frontier agentic coding model (recommended)
- `codestral-2508` (Mistral) - Faster, less accurate

### Model Timeouts

```bash
HACKER_TIMEOUT_MS=45000   # 45 seconds for Finder/Exploiter
ENGINEER_TIMEOUT_MS=90000 # 90 seconds for Engineer
```

**Adjust based on**:
- Model speed
- Network latency
- Complexity of code

### Max Tokens

```bash
HACKER_MAX_TOKENS=4000    # Max output tokens for Finder/Exploiter
ENGINEER_MAX_TOKENS=3000  # Max output tokens for Engineer
```

**Adjust based on**:
- Code file size
- Complexity of patches
- Cost considerations

---

## Server Configuration

### Backend

```bash
PORT=8000
BACKEND_URL=http://localhost:8000
```

**Production**:
```bash
PORT=8000
BACKEND_URL=https://api.aegis-security.dev
```

### Frontend

```bash
FRONTEND_URL=http://localhost:3000
```

**Production**:
```bash
FRONTEND_URL=https://aegis-security.dev
```

### CORS

CORS is configured in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production**: Update `allow_origins` to your production domain.

---

## Scanner Configuration

### Semgrep Binary

```bash
SEMGREP_BIN=""  # Auto-detect if empty
```

**Auto-detection order**:
1. `SEMGREP_BIN` environment variable
2. `semgrep` in PATH
3. `/opt/homebrew/bin/semgrep` (macOS Homebrew)
4. `/usr/local/bin/semgrep` (Linux)
5. `$VIRTUAL_ENV/bin/semgrep` (Python venv)
6. Docker fallback

**Manual path**:
```bash
SEMGREP_BIN=/usr/local/bin/semgrep
```

### Semgrep Docker

```bash
SEMGREP_DOCKER_IMAGE=semgrep/semgrep:latest
```

**Custom image**:
```bash
SEMGREP_DOCKER_IMAGE=semgrep/semgrep:1.50.0
```

### Semgrep Timeout

```bash
SEMGREP_TIMEOUT=180  # 3 minutes
```

**Adjust based on**:
- Repository size
- Number of files
- Semgrep rules

---

## Docker Configuration

### Sandbox Image

```bash
SANDBOX_IMAGE=aegis-sandbox:latest
```

**Build**:
```bash
bash build-sandbox.sh
```

### Sandbox Limits

```bash
SANDBOX_TIMEOUT=30        # Exploit execution timeout (seconds)
TEST_TIMEOUT=45           # Test execution timeout (seconds)
SANDBOX_MEM_LIMIT=256m    # Memory limit
SANDBOX_CPU_QUOTA=50000   # CPU quota (50% of one core)
```

**Adjust based on**:
- Exploit complexity
- Test suite size
- Available resources

### Docker Daemon

Ensure Docker is running:

```bash
docker ps
```

If not running:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

---

## RAG Configuration

### Vector Database

```bash
VECTOR_DB_DIR=./aegis_vector_db
```

**Production**: Use persistent volume or cloud storage.

### RAG Parameters

```bash
RAG_TOP_K=5                  # Number of related files to retrieve
RAG_DISTANCE_THRESHOLD=1.5   # Max distance for relevant results
```

**Adjust based on**:
- Codebase size
- Code similarity
- Agent context window

### Indexing

**Automatic**: Triggered when adding a repository

**Manual**:
```python
from rag.indexer import index_repository

index_repository(
    repo_path="/path/to/repo",
    repo_name="owner/repo"
)
```

---

## Agent Configuration

### Retry Logic

```bash
MAX_PATCH_RETRIES=3  # Max attempts for Engineer before escalating
```

**Adjust based on**:
- Patch complexity
- Model accuracy
- Time constraints

### Agent Behavior

**Demo Mode**:
```bash
DEMO_MODE=true
```

**Purpose**: Simulate vulnerabilities for testing

**Behavior**:
- Exploits always succeed
- Tests always pass
- Patches always work

**Use Cases**:
- Testing pipeline
- Demo presentations
- Development without real vulnerabilities

---

## Advanced Configuration

### Logging

**File**: `config.py`

```python
LOG_FORMAT = "[%(asctime)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
```

**Log Level**:
```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
```

### Database

**Development**: SQLite
```python
DATABASE_URL = "sqlite:///./aegis.db"
```

**Production**: PostgreSQL
```python
DATABASE_URL = "postgresql://user:password@localhost/aegis"
```

**Migration**:
```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Update config.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis.db")

# Run migrations
alembic upgrade head
```

### File Types

**File**: `config.py`

```python
CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
```

**Add language**:
```python
CODE_EXTENSIONS.add(".rs")  # Rust
CODE_EXTENSIONS.add(".cpp") # C++
```

### Paths

```bash
REPOS_DIR=./repos              # Cloned repositories
VECTOR_DB_DIR=./aegis_vector_db # ChromaDB storage
```

**Production**: Use absolute paths or persistent volumes.

---

## Environment-Specific Configurations

### Development

```bash
# .env.development
PORT=8000
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
DEMO_MODE=true
LOG_LEVEL=DEBUG
```

### Staging

```bash
# .env.staging
PORT=8000
FRONTEND_URL=https://staging.aegis-security.dev
BACKEND_URL=https://api-staging.aegis-security.dev
DEMO_MODE=false
LOG_LEVEL=INFO
```

### Production

```bash
# .env.production
PORT=8000
FRONTEND_URL=https://aegis-security.dev
BACKEND_URL=https://api.aegis-security.dev
DEMO_MODE=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://user:password@db.aegis-security.dev/aegis
```

---

## Security Best Practices

### API Keys

- **Never commit** `.env` to version control
- **Use secrets manager** in production (AWS Secrets Manager, HashiCorp Vault)
- **Rotate keys** regularly
- **Use different keys** for dev/staging/prod

### GitHub Token

- **Use fine-grained tokens** with minimal scopes
- **Set expiration** (90 days recommended)
- **Revoke unused tokens**

### Webhook Secret

- **Use strong random secret** (32+ characters)
- **Never share** webhook secret
- **Rotate periodically**

### Database

- **Encrypt GitHub tokens** in production
- **Use SSL/TLS** for database connections
- **Backup regularly**

---

## Troubleshooting

### API Key Issues

**Error**: `Invalid API key`

**Solution**:
1. Check key is correct in `.env`
2. Verify key is active on provider dashboard
3. Check for extra spaces or quotes

### GitHub Token Issues

**Error**: `Bad credentials`

**Solution**:
1. Regenerate token with correct scopes
2. Update `.env` with new token
3. Restart backend

### Webhook Issues

**Error**: `Invalid signature`

**Solution**:
1. Verify `GITHUB_WEBHOOK_SECRET` matches GitHub webhook configuration
2. Check webhook is sending `X-Hub-Signature-256` header
3. Test with ngrok for local development

### Docker Issues

**Error**: `Docker daemon not running`

**Solution**:
1. Start Docker daemon
2. Check Docker is accessible: `docker ps`
3. Rebuild sandbox: `bash build-sandbox.sh`

### RAG Issues

**Error**: `ChromaDB not found`

**Solution**:
1. Check `VECTOR_DB_DIR` exists
2. Re-index repository
3. Check disk space

---

## Configuration Validation

### Check Configuration

```python
python -c "import config; print('Configuration loaded successfully')"
```

### Test API Keys

```python
from mistralai.client import Mistral
from groq import Groq

# Test Mistral
mistral = Mistral(api_key=config.MISTRAL_API_KEY)
print("Mistral: OK")

# Test Groq
groq = Groq(api_key=config.GROQ_API_KEY)
print("Groq: OK")
```

### Test GitHub Token

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

### Test Webhook Secret

```bash
echo -n "test" | openssl dgst -sha256 -hmac "$GITHUB_WEBHOOK_SECRET"
```

---

## Conclusion

Proper configuration is critical for Aegis to function correctly. Follow this guide to set up your environment, and refer to the [Troubleshooting Guide](TROUBLESHOOTING.md) if you encounter issues.

---

**Last Updated**: April 25, 2026  
**Status**: 🟢 Production Ready

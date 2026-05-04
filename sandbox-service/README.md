# Aegis Sandbox Service

Tiny microservice for executing exploit scripts in isolated Docker containers.

## Features

- ✅ Isolated Docker execution
- ✅ No network access
- ✅ Memory limits (256MB)
- ✅ CPU limits (50%)
- ✅ Timeout protection (60s)
- ✅ API key authentication
- ✅ Auto-scales to zero (free tier)

## Deployment to Fly.io

### Prerequisites
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login
```

### Deploy
```bash
cd sandbox-service

# Create app (first time only)
fly launch --name aegis-sandbox --region sjc

# Set API key secret
fly secrets set SANDBOX_API_KEY=$(openssl rand -hex 32)

# Deploy
fly deploy

# Check status
fly status

# View logs
fly logs
```

### Test
```bash
# Get your app URL
FLY_URL=$(fly info --json | jq -r .Hostname)

# Health check
curl https://$FLY_URL/health

# Test exploit execution
curl -X POST https://$FLY_URL/execute \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "exploit_script": "print(\"VULNERABLE: Test exploit\")",
    "repo_url": "https://github.com/test/repo",
    "commit_sha": "abc123"
  }'
```

## API Endpoints

### POST /execute
Execute an exploit script in isolated container.

**Request:**
```json
{
  "exploit_script": "import requests\n...",
  "repo_url": "https://github.com/user/repo",
  "commit_sha": "abc123",
  "is_verification": false
}
```

**Response:**
```json
{
  "exploit_succeeded": true,
  "exit_code": 0,
  "stdout": "VULNERABLE: SQL Injection confirmed",
  "stderr": "",
  "execution_time_seconds": 3.2
}
```

### POST /verify-patch
Verify that a patch blocks the exploit (same as /execute).

### GET /health
Health check endpoint.

## Security

- API key required (X-API-Key header)
- No network access in containers
- Memory limited to 256MB
- CPU limited to 50%
- Timeout after 60 seconds
- Non-root user
- All capabilities dropped

## Cost

**Fly.io Free Tier:**
- 3 VMs × 256MB RAM
- Auto-scales to zero when idle
- **Cost: $0/month**

## Environment Variables

- `SANDBOX_API_KEY` - Required. API key for authentication.
- `PORT` - Optional. Default: 8080

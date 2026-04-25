# 📡 Aegis API Reference

Complete API documentation for all Aegis endpoints.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Scan Endpoints](#scan-endpoints)
3. [Repository Endpoints](#repository-endpoints)
4. [Webhook Endpoints](#webhook-endpoints)
5. [Auth Endpoints](#auth-endpoints)
6. [Scheduler Endpoints](#scheduler-endpoints)
7. [Health Check](#health-check)
8. [Error Responses](#error-responses)
9. [SSE Events](#sse-events)

---

## Base URL

```
Development: http://localhost:8000
Production: https://api.aegis-security.dev
```

---

## Authentication

Most endpoints require GitHub OAuth authentication. Include the user's GitHub token in the request:

```http
Authorization: Bearer <github_token>
```

---

## Scan Endpoints

### GET /api/scans/live

**Description**: Server-Sent Events (SSE) stream for real-time scan updates

**Authentication**: Optional (can filter by repo_id)

**Query Parameters**:
- `repo_id` (optional): Filter scans by repository ID

**Response**: SSE stream

**Event Format**:
```
event: scan_update
data: {"id": 123, "status": "exploiting", "agent_message": "Writing exploit..."}

event: heartbeat
data: {"timestamp": "2026-04-25T10:30:00Z"}
```

**Example**:
```javascript
const eventSource = new EventSource('/api/scans/live?repo_id=1');

eventSource.addEventListener('scan_update', (event) => {
    const scan = JSON.parse(event.data);
    console.log('Scan update:', scan);
});

eventSource.addEventListener('heartbeat', (event) => {
    console.log('Connection alive');
});
```

---

### GET /api/scans

**Description**: List recent scans (initial page load)

**Authentication**: Optional

**Query Parameters**:
- `repo_id` (optional): Filter by repository ID
- `limit` (optional): Number of scans to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
    "scans": [
        {
            "id": 123,
            "repo_id": 1,
            "commit_sha": "abc123",
            "branch": "main",
            "status": "fixed",
            "vulnerability_type": "SQL Injection",
            "severity": "CRITICAL",
            "vulnerable_file": "app.py",
            "exploit_output": "VULNERABLE: SQL Injection confirmed...",
            "patch_diff": "- cursor.execute(f\"SELECT...\")\n+ cursor.execute(\"SELECT...\", (username,))",
            "pr_url": "https://github.com/owner/repo/pull/42",
            "current_agent": "verifier",
            "agent_message": "Patch verified successfully",
            "patch_attempts": 1,
            "created_at": "2026-04-25T10:00:00Z",
            "completed_at": "2026-04-25T10:05:00Z"
        }
    ],
    "total": 100,
    "limit": 50,
    "offset": 0
}
```

---

### GET /api/scans/{scan_id}

**Description**: Get specific scan details

**Authentication**: Optional

**Path Parameters**:
- `scan_id`: Scan ID

**Response**:
```json
{
    "id": 123,
    "repo_id": 1,
    "repo_name": "owner/repo",
    "commit_sha": "abc123",
    "branch": "main",
    "status": "fixed",
    "vulnerability_type": "SQL Injection",
    "severity": "CRITICAL",
    "vulnerable_file": "app.py",
    "exploit_output": "VULNERABLE: SQL Injection confirmed\n[*] Payload: ' OR '1'='1\n[*] Records dumped: [(1, 'admin'), (2, 'user')]",
    "patch_diff": "- cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")\n+ cursor.execute(\"SELECT * FROM users WHERE name = ?\", (username,))",
    "pr_url": "https://github.com/owner/repo/pull/42",
    "original_code": "def get_user(username):\n    cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")\n    return cursor.fetchone()",
    "exploit_script": "#!/usr/bin/env python3\nimport os\nimport sys\n...",
    "findings_json": "[{\"file\": \"app.py\", \"vuln_type\": \"SQL Injection\", ...}]",
    "current_agent": "verifier",
    "agent_message": "Patch verified successfully",
    "patch_attempts": 1,
    "error_message": null,
    "created_at": "2026-04-25T10:00:00Z",
    "completed_at": "2026-04-25T10:05:00Z"
}
```

---

### POST /api/scans/trigger

**Description**: Manually trigger scan on latest commit

**Authentication**: Required

**Request Body**:
```json
{
    "repo_full_name": "owner/repo",
    "branch": "main"
}
```

**Response**:
```json
{
    "message": "Scan triggered successfully",
    "scan_id": 124,
    "commit_sha": "def456"
}
```

**Error Responses**:
- `404`: Repository not found
- `500`: Failed to fetch latest commit

---

### POST /api/scans/trigger-direct

**Description**: Trigger scan with known commit SHA

**Authentication**: Required

**Request Body**:
```json
{
    "repo_full_name": "owner/repo",
    "commit_sha": "abc123",
    "branch": "main"
}
```

**Response**:
```json
{
    "message": "Scan triggered successfully",
    "scan_id": 125
}
```

---

### GET /api/stats

**Description**: Aggregate statistics

**Authentication**: Optional

**Query Parameters**:
- `user_id` (optional): Filter by user ID

**Response**:
```json
{
    "total_repos": 5,
    "total_scans": 100,
    "total_fixes": 42,
    "total_vulnerabilities": 50,
    "vulnerabilities_by_type": {
        "SQL Injection": 20,
        "XSS": 15,
        "Path Traversal": 10,
        "Command Injection": 5
    },
    "vulnerabilities_by_severity": {
        "CRITICAL": 10,
        "HIGH": 20,
        "MEDIUM": 15,
        "LOW": 5
    },
    "scans_by_status": {
        "fixed": 42,
        "failed": 5,
        "false_positive": 3,
        "clean": 50
    }
}
```

---

## Repository Endpoints

### POST /api/repos

**Description**: Add repository + install webhook + trigger RAG index

**Authentication**: Required

**Request Body**:
```json
{
    "user_id": 1,
    "repo_url": "https://github.com/owner/repo"
}
```

**Response**:
```json
{
    "id": 1,
    "full_name": "owner/repo",
    "webhook_id": 12345,
    "is_indexed": false,
    "status": "setting_up",
    "created_at": "2026-04-25T10:00:00Z"
}
```

**Error Responses**:
- `400`: Invalid repo URL
- `404`: User not found
- `409`: Repository already exists
- `500`: Failed to install webhook

---

### GET /api/repos

**Description**: List all repositories for a user

**Authentication**: Required

**Query Parameters**:
- `user_id`: User ID

**Response**:
```json
{
    "repos": [
        {
            "id": 1,
            "full_name": "owner/repo",
            "webhook_id": 12345,
            "is_indexed": true,
            "status": "monitoring",
            "created_at": "2026-04-25T10:00:00Z"
        }
    ]
}
```

---

### GET /api/repos/{repo_id}

**Description**: Get repository details

**Authentication**: Required

**Path Parameters**:
- `repo_id`: Repository ID

**Response**:
```json
{
    "id": 1,
    "full_name": "owner/repo",
    "html_url": "https://github.com/owner/repo",
    "webhook_id": 12345,
    "is_indexed": true,
    "status": "monitoring",
    "created_at": "2026-04-25T10:00:00Z",
    "scans": [
        {
            "id": 123,
            "commit_sha": "abc123",
            "status": "fixed",
            "created_at": "2026-04-25T10:00:00Z"
        }
    ]
}
```

---

### DELETE /api/repos/{repo_id}

**Description**: Remove repository + uninstall webhook

**Authentication**: Required

**Path Parameters**:
- `repo_id`: Repository ID

**Response**:
```json
{
    "message": "Repository removed successfully"
}
```

**Error Responses**:
- `404`: Repository not found
- `500`: Failed to uninstall webhook

---

## Webhook Endpoints

### POST /webhook/github

**Description**: GitHub webhook handler (push + PR events)

**Authentication**: HMAC-SHA256 signature verification

**Headers**:
- `X-Hub-Signature-256`: HMAC signature
- `X-GitHub-Event`: Event type (push, pull_request)

**Request Body**: GitHub webhook payload

**Response**:
```json
{
    "message": "Webhook received",
    "scan_id": 126
}
```

**Error Responses**:
- `400`: Invalid signature
- `400`: Unsupported event type
- `500`: Pipeline failed to start

---

## Auth Endpoints

### GET /api/auth/github

**Description**: Initiate GitHub OAuth flow

**Authentication**: None

**Response**: Redirect to GitHub OAuth

---

### GET /api/auth/github/callback

**Description**: GitHub OAuth callback

**Authentication**: None

**Query Parameters**:
- `code`: OAuth authorization code

**Response**: Redirect to frontend with token

---

### GET /api/auth/user

**Description**: Get current user info

**Authentication**: Required

**Response**:
```json
{
    "id": 1,
    "github_id": 12345,
    "github_username": "johndoe",
    "github_avatar_url": "https://avatars.githubusercontent.com/u/12345",
    "created_at": "2026-04-25T10:00:00Z"
}
```

---

## Scheduler Endpoints

### POST /api/scheduler/start

**Description**: Start autonomous scanning scheduler

**Authentication**: Required (admin only)

**Response**:
```json
{
    "message": "Scheduler started",
    "interval_minutes": 60
}
```

---

### POST /api/scheduler/stop

**Description**: Stop autonomous scanning scheduler

**Authentication**: Required (admin only)

**Response**:
```json
{
    "message": "Scheduler stopped"
}
```

---

### GET /api/scheduler/status

**Description**: Get scheduler status

**Authentication**: Required

**Response**:
```json
{
    "running": true,
    "interval_minutes": 60,
    "last_run": "2026-04-25T10:00:00Z",
    "next_run": "2026-04-25T11:00:00Z"
}
```

---

## Health Check

### GET /health

**Description**: System health status

**Authentication**: None

**Response**:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "docker": "available",
    "semgrep": "available",
    "rag": "indexed",
    "timestamp": "2026-04-25T10:00:00Z"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
    "error": "Error message",
    "detail": "Detailed error description",
    "status_code": 400
}
```

### Common Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error

---

## SSE Events

### Event Types

#### scan_update
```json
{
    "id": 123,
    "status": "exploiting",
    "current_agent": "exploiter",
    "agent_message": "Writing exploit for SQL Injection...",
    "patch_attempts": 0,
    "created_at": "2026-04-25T10:00:00Z"
}
```

#### heartbeat
```json
{
    "timestamp": "2026-04-25T10:00:00Z"
}
```

### Connection Management

**Reconnection**: Frontend automatically reconnects on disconnect

**Timeout**: 30 seconds between heartbeats

**Error Handling**: Frontend displays connection status

---

## Rate Limiting

**Current**: No rate limiting (development)

**Future**: 
- 100 requests/minute per user
- 1000 requests/hour per user
- Webhook endpoints excluded

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters**:
- `limit`: Number of items per page (default: 50, max: 100)
- `offset`: Number of items to skip (default: 0)

**Response**:
```json
{
    "items": [...],
    "total": 100,
    "limit": 50,
    "offset": 0,
    "has_more": true
}
```

---

## Filtering

Endpoints that return lists support filtering:

**Query Parameters**:
- `status`: Filter by status (e.g., `fixed`, `failed`)
- `severity`: Filter by severity (e.g., `CRITICAL`, `HIGH`)
- `repo_id`: Filter by repository ID

**Example**:
```
GET /api/scans?status=fixed&severity=CRITICAL&limit=10
```

---

## Sorting

Endpoints that return lists support sorting:

**Query Parameters**:
- `sort_by`: Field to sort by (e.g., `created_at`, `severity`)
- `sort_order`: Sort order (`asc` or `desc`, default: `desc`)

**Example**:
```
GET /api/scans?sort_by=created_at&sort_order=desc
```

---

## Webhooks

### GitHub Webhook Configuration

**Payload URL**: `https://api.aegis-security.dev/webhook/github`

**Content Type**: `application/json`

**Secret**: Set in `.env` as `GITHUB_WEBHOOK_SECRET`

**Events**:
- Push events
- Pull request events

**SSL Verification**: Enabled

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_github_token"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# List scans
response = requests.get(f"{BASE_URL}/api/scans", headers=headers)
scans = response.json()["scans"]

# Trigger scan
response = requests.post(
    f"{BASE_URL}/api/scans/trigger",
    headers=headers,
    json={"repo_full_name": "owner/repo", "branch": "main"}
)
scan_id = response.json()["scan_id"]

# SSE stream
import sseclient

response = requests.get(f"{BASE_URL}/api/scans/live", stream=True)
client = sseclient.SSEClient(response)

for event in client.events():
    if event.event == "scan_update":
        scan = json.loads(event.data)
        print(f"Scan {scan['id']}: {scan['status']}")
```

### JavaScript

```javascript
const BASE_URL = "http://localhost:8000";
const TOKEN = "your_github_token";

const headers = {
    "Authorization": `Bearer ${TOKEN}`
};

// List scans
const response = await fetch(`${BASE_URL}/api/scans`, { headers });
const { scans } = await response.json();

// Trigger scan
const response = await fetch(`${BASE_URL}/api/scans/trigger`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ repo_full_name: "owner/repo", branch: "main" })
});
const { scan_id } = await response.json();

// SSE stream
const eventSource = new EventSource(`${BASE_URL}/api/scans/live`);

eventSource.addEventListener("scan_update", (event) => {
    const scan = JSON.parse(event.data);
    console.log(`Scan ${scan.id}: ${scan.status}`);
});
```

---

## Conclusion

This API reference covers all Aegis endpoints. For more details, see the [Architecture Guide](ARCHITECTURE.md) and [Development Guide](DEVELOPMENT.md).

---

**Last Updated**: April 25, 2026  
**Status**: 🟢 Production Ready

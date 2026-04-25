# Aegis API Reference

## Overview

Aegis provides a comprehensive REST API for repository management, scan monitoring, and system administration. The API is built with FastAPI and includes real-time updates via Server-Sent Events (SSE).

## Base Configuration

- **Base URL**: `http://localhost:8000` (development)
- **Content-Type**: `application/json`
- **Authentication**: GitHub OAuth (for multi-user setups)
- **Rate Limiting**: Applied per endpoint

## Core Endpoints

### Health and Status

#### GET /health
**Purpose**: System health check with component status

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "docker": "healthy", 
    "groq_api": "configured",
    "mistral_api": "configured",
    "github_token": "configured"
  },
  "version": "2.0.0"
}
```

**Status Values**:
- `healthy`: All systems operational
- `degraded`: Some components unavailable

#### GET /ready
**Purpose**: Readiness probe for load balancers

**Response**: 
- `200`: System ready to process scans
- `503`: Docker unavailable, not ready

### Repository Management

#### GET /api/repos
**Purpose**: List all monitored repositories

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `limit` (int): Results per page (default: 20)

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "full_name": "user/repository",
      "clone_url": "https://github.com/user/repository.git",
      "default_branch": "main",
      "is_indexed": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "pages": 1
  }
}
```

#### POST /api/repos
**Purpose**: Add new repository for monitoring

**Request Body**:
```json
{
  "full_name": "user/repository",
  "clone_url": "https://github.com/user/repository.git",
  "default_branch": "main"
}
```

**Response**:
```json
{
  "id": 1,
  "full_name": "user/repository",
  "clone_url": "https://github.com/user/repository.git",
  "default_branch": "main",
  "is_indexed": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/repos/{repo_id}
**Purpose**: Get repository details with recent scans

**Response**:
```json
{
  "id": 1,
  "full_name": "user/repository",
  "clone_url": "https://github.com/user/repository.git",
  "default_branch": "main",
  "is_indexed": true,
  "recent_scans": [
    {
      "id": 10,
      "commit_sha": "abc123...",
      "branch": "main",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### DELETE /api/repos/{repo_id}
**Purpose**: Remove repository from monitoring

**Response**: `204 No Content`

### Scan Management

#### GET /api/scans
**Purpose**: List all scans with filtering

**Query Parameters**:
- `repo_id` (int): Filter by repository
- `status` (str): Filter by scan status
- `page` (int): Page number
- `limit` (int): Results per page

**Response**:
```json
{
  "data": [
    {
      "id": 10,
      "repo_id": 1,
      "commit_sha": "abc123def456...",
      "branch": "main",
      "status": "completed",
      "vulnerabilities_found": 2,
      "vulnerabilities_fixed": 1,
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:35:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "pages": 1
  }
}
```

#### GET /api/scans/{scan_id}
**Purpose**: Get detailed scan results

**Response**:
```json
{
  "id": 10,
  "repo_id": 1,
  "commit_sha": "abc123def456...",
  "branch": "main",
  "status": "completed",
  "vulnerabilities_found": 2,
  "vulnerabilities_fixed": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "findings": [
    {
      "id": 1,
      "vulnerability_type": "SQL Injection",
      "severity": "CRITICAL",
      "cwe_id": "CWE-89",
      "file_path": "app.py",
      "line_number": 45,
      "status": "fixed",
      "exploit_confirmed": true,
      "patch_applied": true,
      "pr_url": "https://github.com/user/repo/pull/123"
    }
  ],
  "execution_log": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "agent": "pre_process",
      "message": "Repository cloned successfully"
    },
    {
      "timestamp": "2024-01-15T10:30:15Z", 
      "agent": "finder",
      "message": "Found 2 potential vulnerabilities"
    }
  ]
}
```

#### POST /api/scans
**Purpose**: Trigger manual scan

**Request Body**:
```json
{
  "repo_id": 1,
  "branch": "main",
  "commit_sha": "abc123def456..." // optional, uses latest if omitted
}
```

**Response**:
```json
{
  "scan_id": 11,
  "status": "queued",
  "message": "Scan queued for execution"
}
```

#### GET /api/scans/{scan_id}/stream
**Purpose**: Real-time scan progress via Server-Sent Events

**Response**: SSE stream
```
data: {"agent": "pre_process", "message": "Cloning repository...", "timestamp": "2024-01-15T10:30:00Z"}

data: {"agent": "finder", "message": "Analyzing 5 Semgrep findings...", "timestamp": "2024-01-15T10:30:15Z"}

data: {"agent": "exploiter", "message": "Generated exploit for SQL injection", "timestamp": "2024-01-15T10:30:45Z"}
```

### Webhook Endpoints

#### POST /webhook/github
**Purpose**: GitHub webhook handler

**Headers**:
- `X-Hub-Signature-256`: HMAC-SHA256 signature
- `X-GitHub-Event`: Event type (push, pull_request)

**Rate Limit**: 30 requests/minute

**Request Body**: GitHub webhook payload

**Response**:
```json
{
  "message": "Webhook received",
  "commit": "abc123de"
}
```

### Intelligence and Analytics

#### GET /api/intelligence/patterns
**Purpose**: Get learned vulnerability patterns

**Response**:
```json
{
  "patterns": [
    {
      "pattern_type": "sql_injection",
      "confidence": 0.95,
      "occurrences": 15,
      "last_seen": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### GET /api/intelligence/trends
**Purpose**: Vulnerability trend analysis

**Query Parameters**:
- `days` (int): Time period (default: 30)
- `repo_id` (int): Filter by repository

**Response**:
```json
{
  "trends": {
    "total_scans": 45,
    "vulnerabilities_found": 23,
    "vulnerabilities_fixed": 18,
    "false_positive_rate": 0.12,
    "avg_remediation_time": "8.5 minutes"
  },
  "by_type": {
    "SQL Injection": 8,
    "XSS": 5,
    "Command Injection": 4
  }
}
```

### Export and Reporting

#### GET /api/export/scans
**Purpose**: Export scan data

**Query Parameters**:
- `format` (str): csv, json, pdf
- `repo_id` (int): Filter by repository
- `start_date` (str): ISO date
- `end_date` (str): ISO date

**Response**: File download or JSON data

#### GET /api/export/findings
**Purpose**: Export vulnerability findings

**Query Parameters**:
- `format` (str): csv, json
- `severity` (str): Filter by severity
- `status` (str): Filter by status

### Authentication (Multi-User Mode)

#### GET /auth/github
**Purpose**: Initiate GitHub OAuth flow

**Response**: Redirect to GitHub authorization

#### GET /auth/callback
**Purpose**: GitHub OAuth callback

**Query Parameters**:
- `code`: Authorization code from GitHub
- `state`: CSRF protection token

**Response**: JWT token or redirect to frontend

#### POST /auth/logout
**Purpose**: Invalidate authentication token

**Response**: `200 OK`

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Repository not found",
    "details": {
      "repo_id": 999
    }
  }
}
```

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `204`: No Content
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Rate Limited
- `500`: Internal Server Error
- `503`: Service Unavailable

### Error Codes
- `VALIDATION_ERROR`: Invalid request parameters
- `AUTHENTICATION_REQUIRED`: Missing or invalid authentication
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `DOCKER_UNAVAILABLE`: Docker daemon not running
- `GITHUB_API_ERROR`: GitHub API request failed

## Rate Limiting

### Limits by Endpoint
- `/webhook/github`: 30 requests/minute
- `/api/scans` (POST): 10 requests/minute
- Other endpoints: 100 requests/minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642262400
```

## WebSocket/SSE Events

### Scan Progress Events
```javascript
// Connect to scan progress stream
const eventSource = new EventSource('/api/scans/123/stream');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log(`${data.agent}: ${data.message}`);
};
```

### Event Types
- `scan_started`: Scan initiated
- `agent_update`: Agent progress update
- `vulnerability_found`: New vulnerability detected
- `exploit_confirmed`: Exploit successfully executed
- `patch_generated`: Fix created
- `pr_created`: Pull request opened
- `scan_completed`: Scan finished
- `scan_failed`: Scan encountered error

## SDK Examples

### Python Client
```python
import requests

class AegisClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def add_repository(self, full_name, clone_url, branch="main"):
        response = requests.post(f"{self.base_url}/api/repos", json={
            "full_name": full_name,
            "clone_url": clone_url,
            "default_branch": branch
        })
        return response.json()
    
    def trigger_scan(self, repo_id, branch="main"):
        response = requests.post(f"{self.base_url}/api/scans", json={
            "repo_id": repo_id,
            "branch": branch
        })
        return response.json()
    
    def get_scan_results(self, scan_id):
        response = requests.get(f"{self.base_url}/api/scans/{scan_id}")
        return response.json()

# Usage
client = AegisClient()
repo = client.add_repository("user/repo", "https://github.com/user/repo.git")
scan = client.trigger_scan(repo["id"])
results = client.get_scan_results(scan["scan_id"])
```

### JavaScript Client
```javascript
class AegisClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }
  
  async addRepository(fullName, cloneUrl, branch = 'main') {
    const response = await fetch(`${this.baseUrl}/api/repos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: fullName,
        clone_url: cloneUrl,
        default_branch: branch
      })
    });
    return response.json();
  }
  
  async triggerScan(repoId, branch = 'main') {
    const response = await fetch(`${this.baseUrl}/api/scans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId, branch })
    });
    return response.json();
  }
  
  streamScanProgress(scanId, callback) {
    const eventSource = new EventSource(`${this.baseUrl}/api/scans/${scanId}/stream`);
    eventSource.onmessage = (event) => {
      callback(JSON.parse(event.data));
    };
    return eventSource;
  }
}
```

This API provides comprehensive access to all Aegis functionality with real-time monitoring capabilities and robust error handling.
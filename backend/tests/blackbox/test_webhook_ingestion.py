import os
import hmac
import hashlib
import json
import httpx
import pytest

BASE_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dummy_secret_for_testing")

def generate_signature(payload: bytes, secret: str) -> str:
    """Generate GitHub X-Hub-Signature-256 for a payload."""
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

def test_webhook_unauthorized():
    """Verify that a webhook request without a valid signature is rejected."""
    payload = json.dumps({"action": "opened", "pull_request": {"number": 1}}).encode("utf-8")
    
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.post(
                "/api/v1/github/webhook",
                content=payload,
                headers={"X-GitHub-Event": "pull_request"} # Missing signature
            )
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # Unauthorized or Bad Request
        assert response.status_code in [400, 401, 403]

def test_webhook_push_event():
    """Verify that a properly signed Push event is accepted."""
    payload_dict = {
        "ref": "refs/heads/main",
        "repository": {
            "id": 12345,
            "full_name": "mitu1046/aegis-test-repo",
            "html_url": "https://github.com/mitu1046/aegis-test-repo"
        },
        "head_commit": {
            "id": "abcdef123456"
        }
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.post(
                "/api/v1/github/webhook",
                content=payload,
                headers={
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json"
                }
            )
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # Accepted for processing or OK
        assert response.status_code in [200, 202]

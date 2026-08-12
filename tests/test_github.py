import pytest
import hmac
import hashlib
import config
from github_integration.webhook import verify_signature, extract_push_info
from github_integration.app_auth import generate_app_jwt

def test_webhook_signature_verification():
    payload = b'{"ref": "refs/heads/main", "after": "1234567890abcdef"}'
    secret = config.GITHUB_WEBHOOK_SECRET or "testsecret"
    
    hash_obj = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    sig = "sha256=" + hash_obj.hexdigest()
    
    assert verify_signature(payload, sig) is True
    assert verify_signature(payload, "sha256=invalid") is False
    assert verify_signature(payload, "") is False

def test_extract_push_info():
    payload = {
        "repository": {
            "full_name": "owner/repo",
            "clone_url": "https://github.com/owner/repo.git"
        },
        "ref": "refs/heads/feature",
        "after": "9876543210fedcba",
        "pusher": {"name": "alice"},
        "commits": [
            {
                "message": "fix vulnerability",
                "added": ["src/main.py"],
                "modified": ["config.json"]
            }
        ]
    }
    info = extract_push_info(payload)
    assert info["repo_name"] == "owner/repo"
    assert info["branch"] == "feature"
    assert info["commit_sha"] == "9876543210fedcba"
    assert info["pusher"] == "alice"
    assert "src/main.py" in info["files_changed"]
    assert "config.json" in info["files_changed"]

def test_github_app_jwt():
    jwt_token = generate_app_jwt()
    assert isinstance(jwt_token, str)
    assert len(jwt_token) > 50

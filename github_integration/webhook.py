import hashlib
import hmac
import config

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook actually came from GitHub by checking the signature.
    """
    if not signature_header:
        return False
        
    hash_object = hmac.new(
        config.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

def extract_push_info(payload: dict) -> dict:
    """
    Extract only the required information from the GitHub push webhook payload.
    """
    return {
        "repo_name": payload["repository"]["full_name"],
        "repo_url": payload["repository"]["clone_url"],
        "branch": payload["ref"].replace("refs/heads/", ""),
        "commit_sha": payload["after"],
        "commit_message": payload.get("head_commit", {}).get("message", ""),
        "pusher": payload["pusher"]["name"],
        "files_changed": [
            f
            for commit in payload.get("commits", [])
            for f in commit.get("added", []) + commit.get("modified", [])
        ]
    }

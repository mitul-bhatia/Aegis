import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.database import get_db
from backend.app.models.entities import Repository, Scan
from backend.app.api.scans import trigger_scan_direct

logger = logging.getLogger("aegis.api.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook payload HMAC SHA-256 signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
    if not signature_header:
        return False

    hash_object = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


@router.post("/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header("push"),
    x_hub_signature_256: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Handle GitHub push, pull_request, and installation webhooks.
    """
    payload_body = await request.body()
    if not verify_github_signature(payload_body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    payload = json.loads(payload_body.decode("utf-8"))
    logger.info(f"Received GitHub webhook event: {x_github_event}")

    # 1. Handle Push events
    if x_github_event == "push":
        repo_data = payload.get("repository", {})
        repo_full_name = repo_data.get("full_name")
        commit_sha = payload.get("after") or "HEAD"
        ref = payload.get("ref", "refs/heads/main")
        branch = ref.replace("refs/heads/", "")

        repo = db.query(Repository).filter(Repository.full_name == repo_full_name).first()
        if repo:
            trigger_scan_direct(repo_id=repo.id, commit_sha=commit_sha, branch=branch, db=db)
            return {"status": "scan_triggered", "repo": repo_full_name, "commit": commit_sha}

    return {"status": "received", "event": x_github_event}

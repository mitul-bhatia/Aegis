"""
Aegis — Repository Management Routes

Handles:
- POST /api/repos     — Add repo + auto-install webhook + trigger RAG index
- GET  /api/repos     — List all repos for a user
- DELETE /api/repos/  — Remove repo + uninstall webhook
"""

import logging
import requests
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

import config
from database.db import get_db
from database.models import User, Repo
from rag.indexer import index_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repos", tags=["repos"])


# ── Request / Response Models ─────────────────────────────
class AddRepoRequest(BaseModel):
    user_id: int
    repo_url: str  # e.g. "https://github.com/user/repo" or "user/repo"


class RepoResponse(BaseModel):
    id: int
    full_name: str
    webhook_id: Optional[int]
    is_indexed: bool
    status: str
    created_at: str


class RepoDetailResponse(RepoResponse):
    html_url: str


# ── Helpers ───────────────────────────────────────────────
def _parse_repo_url(url: str) -> str:
    """
    Normalize a repo URL to 'owner/repo' format.
    Accepts: https://github.com/owner/repo, github.com/owner/repo, owner/repo
    """
    url = url.strip().rstrip("/")
    url = url.replace("https://github.com/", "").replace("http://github.com/", "")
    url = url.replace("github.com/", "")
    # Remove .git suffix if present
    if url.endswith(".git"):
        url = url[:-4]
    return url


def _install_webhook(full_name: str, github_token: str) -> int:
    """
    Install a webhook on a GitHub repo via the API.
    Returns the webhook ID for later cleanup.
    """
    if not config.GITHUB_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_WEBHOOK_SECRET is not configured on the backend",
        )

    webhook_url = f"{config.BACKEND_URL}/webhook/github"

    response = requests.post(
        f"https://api.github.com/repos/{full_name}/hooks",
        json={
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": config.GITHUB_WEBHOOK_SECRET,
                "insecure_ssl": "0",
            },
        },
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )

    if response.status_code not in (201, 200):
        error_msg = response.json().get("message", "Unknown error")
        logger.error(f"Failed to install webhook on {full_name}: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to install webhook: {error_msg}. "
                   f"Make sure your GitHub token has 'admin:repo_hook' permission."
        )

    webhook_id = response.json()["id"]
    logger.info(f"Webhook installed on {full_name} (ID: {webhook_id})")
    return webhook_id


def _uninstall_webhook(full_name: str, webhook_id: int, github_token: str):
    """Remove a webhook from a GitHub repo."""
    response = requests.delete(
        f"https://api.github.com/repos/{full_name}/hooks/{webhook_id}",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    if response.status_code == 204:
        logger.info(f"Webhook {webhook_id} removed from {full_name}")
    else:
        logger.warning(f"Failed to remove webhook {webhook_id} from {full_name}")


def _background_index_repo(repo_id: int, full_name: str, github_token: str):
    """
    Background task: Clone/pull repo and build RAG index.
    Updates repo status when complete.
    """
    from database.db import SessionLocal
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            return

        logger.info(f"Background: Indexing {full_name}...")

        # Clone or pull the repo
        import os
        import subprocess
        repo_path = os.path.join(config.REPOS_DIR, full_name.replace("/", "_"))

        if os.path.exists(repo_path):
            pull_result = subprocess.run(
                ["git", "-C", repo_path, "pull"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if pull_result.returncode != 0:
                raise RuntimeError(f"git pull failed: {pull_result.stderr.strip()}")
        else:
            clone_url = f"https://x-access-token:{github_token}@github.com/{full_name}.git"
            clone_result = subprocess.run(
                ["git", "clone", clone_url, repo_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if clone_result.returncode != 0:
                raise RuntimeError(f"git clone failed: {clone_result.stderr.strip()}")

        # Build RAG index
        num_files = index_repository(repo_path, full_name)
        logger.info(f"Background: Indexed {num_files} files from {full_name}")

        # Update DB
        repo.is_indexed = True
        repo.status = "monitoring"
        db.commit()
        logger.info(f"Background: {full_name} is now being monitored ✅")

    except Exception as e:
        logger.exception(f"Background: Failed to index {full_name}: {e}")
        repo = db.query(Repo).filter(Repo.id == repo_id).first()
        if repo:
            repo.status = "error"
            db.commit()
    finally:
        db.close()


# ── Routes ────────────────────────────────────────────────
@router.post("", response_model=RepoResponse)
def add_repo(
    body: AddRepoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Add a repo to Aegis monitoring.
    1. Validate the user exists
    2. Parse and normalize the repo URL
    3. Install a webhook on the repo via GitHub API
    4. Save to database
    5. Kick off background RAG indexing
    """
    # 1. Get user
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Parse repo URL
    full_name = _parse_repo_url(body.repo_url)
    if "/" not in full_name or len(full_name.split("/")) != 2:
        raise HTTPException(status_code=400, detail=f"Invalid repo: '{full_name}'. Expected 'owner/repo' format.")

    # Check for duplicates
    existing = db.query(Repo).filter(Repo.user_id == user.id, Repo.full_name == full_name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Repo '{full_name}' is already being monitored")

    # 3. Install webhook - Use backend token (has admin:repo_hook) instead of user OAuth token
    # The user's OAuth token might not have webhook permissions
    webhook_token = config.GITHUB_TOKEN if config.GITHUB_TOKEN else user.github_token
    webhook_id = _install_webhook(full_name, webhook_token)

    # 4. Save to DB
    repo = Repo(
        user_id=user.id,
        full_name=full_name,
        webhook_id=webhook_id,
        is_indexed=False,
        status="setting_up",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # 5. Background RAG index
    background_tasks.add_task(_background_index_repo, repo.id, full_name, user.github_token)

    logger.info(f"Repo {full_name} added for user {user.github_username} — indexing in background")

    return RepoResponse(
        id=repo.id,
        full_name=repo.full_name,
        webhook_id=repo.webhook_id,
        is_indexed=repo.is_indexed,
        status=repo.status,
        created_at=str(repo.created_at),
    )


@router.get("")
def list_repos(user_id: int, db: Session = Depends(get_db)):
    """List all monitored repos for a user."""
    repos = db.query(Repo).filter(Repo.user_id == user_id).all()
    return [
        RepoResponse(
            id=r.id,
            full_name=r.full_name,
            webhook_id=r.webhook_id,
            is_indexed=r.is_indexed,
            status=r.status,
            created_at=str(r.created_at),
        )
        for r in repos
    ]


@router.get("/{repo_id}", response_model=RepoDetailResponse)
def get_repo(repo_id: int, db: Session = Depends(get_db)):
    """Get a single monitored repo by ID."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    return RepoDetailResponse(
        id=repo.id,
        full_name=repo.full_name,
        webhook_id=repo.webhook_id,
        is_indexed=repo.is_indexed,
        status=repo.status,
        created_at=str(repo.created_at),
        html_url=f"https://github.com/{repo.full_name}",
    )


@router.delete("/{repo_id}")
def remove_repo(repo_id: int, db: Session = Depends(get_db)):
    """Remove a repo from monitoring and uninstall the webhook."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    # Uninstall webhook from GitHub
    user = db.query(User).filter(User.id == repo.user_id).first()
    if user and repo.webhook_id:
        _uninstall_webhook(repo.full_name, repo.webhook_id, user.github_token)

    db.delete(repo)
    db.commit()

    logger.info(f"Repo {repo.full_name} removed from monitoring")
    return {"message": f"Repo {repo.full_name} removed"}

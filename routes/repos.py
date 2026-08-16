"""
Aegis — Repository Management Routes

Handles:
- POST /api/repos     — Add repo + auto-install webhook + trigger RAG index
- GET  /api/repos     — List all repos for a user
- DELETE /api/repos/  — Remove repo + uninstall webhook
"""

import logging
import math

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from database.db import get_db
from database.models import Repo, User
from rag.indexer import index_repository
from utils.crypto import decrypt_token  # decrypt before using the token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/repos", tags=["repos"])


# ── Request / Response Models ─────────────────────────────
class AddRepoRequest(BaseModel):
    user_id: int
    repo_url: str  # e.g. "https://github.com/user/repo" or "user/repo"


class RepoResponse(BaseModel):
    id: int
    full_name: str
    webhook_id: int | None
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
    url = url.removesuffix(".git")
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
    
    # For local development, GitHub blocks localhost for webhooks (SSRF protection)
    # We will simulate a successful installation so the UI works, but webhooks won't fire.
    if "localhost" in webhook_url or "127.0.0.1" in webhook_url:
        logger.warning(f"⚠️  Webhook URL is localhost: {webhook_url}")
        logger.warning("   Skipping GitHub API call. Webhooks will not work until you use ngrok or deploy.")
        return 999999999  # Dummy webhook ID

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
        logger.error(f"Failed to install webhook on {full_name}: {error_msg} (Status: {response.status_code})")
        
        # Provide specific error messages based on status code
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{full_name}' not found. Make sure:\n"
                       f"1. The repository exists\n"
                       f"2. The repository name is correct (use 'owner/repo' format)\n"
                       f"3. Your GitHub token has access to this repository"
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied for '{full_name}'. Make sure your GitHub token has 'admin:repo_hook' permission."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to install webhook: {error_msg}"
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
        
        # Override token if this repo is managed via a GitHub App Installation
        if repo.installation_id:
            from github_integration.app_auth import get_installation_access_token
            github_token = get_installation_access_token(repo.installation_id)

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
            if not github_token:
                clone_url = f"https://github.com/{full_name}.git"
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

    # 3. Install webhook if not using GitHub App
    webhook_id = None
    if user.github_installation_id:
        logger.info(f"Using GitHub App installation {user.github_installation_id} for {full_name}")
    else:
        # Fallback to manual webhook installation via personal token
        webhook_token = config.GITHUB_TOKEN if config.GITHUB_TOKEN else decrypt_token(user.github_token)
        if not webhook_token:
            raise HTTPException(
                status_code=400,
                detail="Missing GitHub token to manually install webhook."
            )
            
        webhook_id = _install_webhook(full_name, webhook_token)

    # 4. Save to DB
    repo = Repo(
        user_id=user.id,
        full_name=full_name,
        installation_id=user.github_installation_id,
        webhook_id=webhook_id,
        is_indexed=False,
        status="setting_up",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # 5. Background RAG index
    # If using GitHub App, the background task will use the installation token automatically.
    # Only pass the user's OAuth token if we're NOT using the App flow.
    clone_token = ""
    if not user.github_installation_id:
        try:
            clone_token = decrypt_token(user.github_token)
        except Exception:
            clone_token = ""
    background_tasks.add_task(_background_index_repo, repo.id, full_name, clone_token)

    logger.info(f"Repo {full_name} added for user {user.github_username} — indexing in background")

    return RepoResponse(
        id=repo.id,
        full_name=repo.full_name,
        webhook_id=repo.webhook_id,
        is_indexed=repo.is_indexed,
        status=repo.status,
        created_at=str(repo.created_at),
    )



@router.get("/available")
def list_available_repos(user_id: int, db: Session = Depends(get_db)):
    """
    List all repositories the user has granted access to via the GitHub App.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.github_installation_id:
        return {"data": []}
        
    try:
        from github_integration.app_auth import get_installation_access_token
        import requests
        
        token = get_installation_access_token(user.github_installation_id)
        if not token:
            return {"data": []}
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get("https://api.github.com/installation/repositories", headers=headers, timeout=10)
        response.raise_for_status()
        
        repos = response.json().get("repositories", [])
        
        # Filter out repos that are already being monitored
        existing_repos = {r.full_name for r in db.query(Repo).filter(Repo.user_id == user.id).all()}
        
        available = []
        for r in repos:
            full_name = r.get("full_name")
            available.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "full_name": full_name,
                "private": r.get("private"),
                "is_monitored": full_name in existing_repos
            })
            
        return {"data": available}
    except Exception as e:
        logger.error(f"Failed to fetch available repos for user {user.id}: {e}")
        return {"data": [], "error": str(e)}


@router.get("")
def list_repos(user_id: int, page: int = 1, per_page: int = 20, db: Session = Depends(get_db)):
    """
    List all monitored repos for a user with pagination.
    Returns: { data: [...], pagination: { page, per_page, total, total_pages } }
    """
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page

    query = db.query(Repo).filter(Repo.user_id == user_id).order_by(Repo.created_at.desc())
    total = query.count()
    repos = query.offset(offset).limit(per_page).all()

    return {
        "data": [
            RepoResponse(
                id=r.id,
                full_name=r.full_name,
                webhook_id=r.webhook_id,
                is_indexed=r.is_indexed,
                status=r.status,
                created_at=str(r.created_at),
            )
            for r in repos
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page) if total > 0 else 1,
        },
    }


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

    # Uninstall webhook from GitHub — decrypt token before using it
    user = db.query(User).filter(User.id == repo.user_id).first()
    if user and repo.webhook_id:
        _uninstall_webhook(repo.full_name, repo.webhook_id, decrypt_token(user.github_token))

    db.delete(repo)
    db.commit()

    logger.info(f"Repo {repo.full_name} removed from monitoring")
    return {"message": f"Repo {repo.full_name} removed"}


@router.post("/seed-demo")
def seed_demo_repo(body: dict, db: Session = Depends(get_db)):
    """
    Seed a showcase demo repo with sample vulnerability scan history
    so recruiters or visitors can view an active dashboard instantly.
    """
    from database.models import Scan, ScanStatus

    user_id = body.get("user_id", 1)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    demo_repo = Repo(
        user_id=user.id,
        full_name="mitul-bhatia/vulnerable-python-app",
        webhook_id=999999,
        is_indexed=True,
        status="monitoring",
    )
    db.add(demo_repo)
    db.commit()
    db.refresh(demo_repo)

    scan1 = Scan(
        repo_id=demo_repo.id,
        commit_sha="a7b8c9d01234567890abcdef1234567890abcdef",
        branch="main",
        status=ScanStatus.FIXED.value,
        vulnerability_type="SQL Injection (CWE-89)",
        severity="HIGH",
        vulnerable_file="routes/users.py",
        exploit_output="[+] PoC EXPLOIT SUCCESSFUL: Injected payload returned database credentials",
        original_code="""query = f"SELECT * FROM users WHERE username = '{username}'"\ncursor.execute(query)""",
        patch_diff="""- query = f"SELECT * FROM users WHERE username = '{username}'"
+ query = "SELECT * FROM users WHERE username = :username"
+ cursor.execute(query, {"username": username})""",
        pr_url="https://github.com/mitul-bhatia/Aegis/pull/1",
    )
    scan2 = Scan(
        repo_id=demo_repo.id,
        commit_sha="e5f6a7b81234567890abcdef1234567890abcdef",
        branch="main",
        status=ScanStatus.CLEAN.value,
        vulnerability_type=None,
        severity=None,
        vulnerable_file=None,
    )
    db.add_all([scan1, scan2])
    db.commit()

    return {"message": "Demo repo & scan history seeded successfully", "repo_id": demo_repo.id}


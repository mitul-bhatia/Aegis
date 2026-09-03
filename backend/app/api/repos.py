import logging
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional
from backend.app.models.entities import User, Repository
from backend.app.schemas.dtos import (
    RepoInfo,
    RepoCreateRequest,
    AvailableRepo,
)
from backend.app.schemas.common import PaginatedResponse, PaginationMeta
from backend.app.github.client import GitHubClient

logger = logging.getLogger("aegis.api.repos")
router = APIRouter(prefix="/repos", tags=["repos"])


@router.get("/available", response_model=List[AvailableRepo])
def get_available_repos(
    user_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Fetch all GitHub repositories available under the user's GitHub App installation.
    """
    target_user = current_user
    if user_id:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            target_user = u

    if not target_user:
        target_user = db.query(User).first()

    installation_id = target_user.github_installation_id if target_user else None
    
    # Try fetching real repos from GitHub App Installation
    if installation_id:
        try:
            client = GitHubClient(installation_id=installation_id)
            repos = client.list_installation_repos()
            if repos:
                return repos
        except Exception as e:
            logger.warning(f"Could not list installation repos: {e}")

    return []


@router.post("", response_model=RepoInfo)
def add_repository(
    req: RepoCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Link a repository to Aegis for active scanning & monitoring.
    """
    # Clean repo url to extract full_name (e.g. "mitu1046/aegis-test-repo")
    repo_url = req.repo_url.strip()
    if not repo_url.startswith("http") and not repo_url.startswith("git@"):
        raise HTTPException(status_code=422, detail="Invalid repository URL format")
        
    full_name = repo_url.replace("https://github.com/", "").replace(".git", "").strip("/")
    
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Repository).filter(Repository.full_name == full_name).first()
    if existing:
        return RepoInfo(
            id=existing.id,
            full_name=existing.full_name,
            webhook_id=existing.webhook_id,
            is_indexed=existing.is_indexed,
            status=existing.status,
            created_at=existing.created_at.isoformat(),
            html_url=existing.html_url,
        )

    new_repo = Repository(
        user_id=user.id,
        full_name=full_name,
        installation_id=user.github_installation_id,
        html_url=f"https://github.com/{full_name}",
        is_indexed=True,
        status="active",
    )
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)

    return RepoInfo(
        id=new_repo.id,
        full_name=new_repo.full_name,
        webhook_id=new_repo.webhook_id,
        is_indexed=new_repo.is_indexed,
        status=new_repo.status,
        created_at=new_repo.created_at.isoformat(),
        html_url=new_repo.html_url,
    )


@router.get("", response_model=PaginatedResponse[RepoInfo])
def list_repositories(
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List monitored repositories with pagination."""
    query = db.query(Repository)
    if user_id:
        query = query.filter(Repository.user_id == user_id)

    total = query.count()
    total_pages = max(1, math.ceil(total / per_page))
    items = query.order_by(Repository.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    repo_dtos = [
        RepoInfo(
            id=r.id,
            full_name=r.full_name,
            webhook_id=r.webhook_id,
            is_indexed=r.is_indexed,
            status=r.status,
            created_at=r.created_at.isoformat(),
            html_url=r.html_url,
        )
        for r in items
    ]

    return PaginatedResponse(
        data=repo_dtos,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/{repo_id}", response_model=RepoInfo)
def get_repository(
    repo_id: int,
    db: Session = Depends(get_db),
):
    """Get single repository details."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return RepoInfo(
        id=repo.id,
        full_name=repo.full_name,
        webhook_id=repo.webhook_id,
        is_indexed=repo.is_indexed,
        status=repo.status,
        created_at=repo.created_at.isoformat(),
        html_url=repo.html_url,
    )


@router.delete("/{repo_id}")
def delete_repository(
    repo_id: int,
    db: Session = Depends(get_db),
):
    """Unlink a repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    db.delete(repo)
    db.commit()
    return {"message": "Repository removed successfully"}

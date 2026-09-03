import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
import requests

from backend.app.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional, get_current_user
from backend.app.models.entities import User
from backend.app.schemas.dtos import OAuthRequest, InstallationLinkRequest, UserInfo

logger = logging.getLogger("aegis.api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/github", response_model=UserInfo)
def exchange_github_oauth(
    req: OAuthRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Exchange OAuth code for GitHub access token and retrieve/create user profile.
    Sets httpOnly session cookie and returns UserInfo.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub Client ID or Secret not configured")

    # 1. Exchange code for access token with GitHub
    token_url = "https://github.com/login/oauth/access_token"
    token_resp = requests.post(
        token_url,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": req.code,
            "redirect_uri": req.redirect_uri,
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange GitHub code")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))

    # 2. Fetch user profile from GitHub
    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch GitHub profile")

    gh_user = user_resp.json()
    github_id = gh_user["id"]
    username = gh_user["login"]
    avatar_url = gh_user.get("avatar_url", "")

    # 3. Create or update user in database
    user = db.query(User).filter(User.github_id == github_id).first()
    if not user:
        user = User(
            github_id=github_id,
            github_username=username,
            github_avatar_url=avatar_url,
            access_token=access_token,
        )
        db.add(user)
    else:
        user.github_username = username
        user.github_avatar_url = avatar_url
        user.access_token = access_token

    db.commit()
    db.refresh(user)

    # 4. Set Session Cookie
    response.set_cookie(
        key="aegis_session",
        value=str(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
    )
    return user


@router.get("/me", response_model=UserInfo)
def get_current_user_profile(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Return current authenticated user profile."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie("aegis_session")
    response.delete_cookie("aegis_user_id")
    return {"message": "Logged out successfully"}


@router.post("/installation")
def link_github_installation(
    req: InstallationLinkRequest,
    db: Session = Depends(get_db),
):
    """Link GitHub App Installation ID to a user account."""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.github_installation_id = req.installation_id
    db.commit()
    return {"status": "ok", "user_id": user.id, "installation_id": req.installation_id}

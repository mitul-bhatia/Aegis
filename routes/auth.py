"""
Aegis — GitHub OAuth Routes

Handles:
- POST /api/auth/github — exchange OAuth code for user session
- GET /api/user — return current user info
"""

import logging
import requests
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from database.db import get_db
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


class GitHubCodeRequest(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: int
    github_id: int
    github_username: str
    github_avatar_url: str


@router.get("/github/callback")
def github_oauth_callback_redirect(code: str, db: Session = Depends(get_db)):
    """
    Handle GitHub OAuth callback directly (server-side redirect).
    This bypasses the frontend API call that's failing due to ngrok SSL issues.
    """
    try:
        # Step 1: Exchange code for access token
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": config.GITHUB_CLIENT_ID,
                "client_secret": config.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )

        if token_response.status_code != 200:
            return RedirectResponse(url=f"{config.FRONTEND_URL}/?error=token_exchange_failed")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            error = token_data.get("error_description", "Unknown error")
            return RedirectResponse(url=f"{config.FRONTEND_URL}/?error={error}")

        # Step 2: Get user info from GitHub
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )

        if user_response.status_code != 200:
            return RedirectResponse(url=f"{config.FRONTEND_URL}/?error=github_user_fetch_failed")

        gh_user = user_response.json()

        # Step 3: Upsert user in database
        user = db.query(User).filter(User.github_id == gh_user["id"]).first()

        if user:
            # Existing user — update token
            user.github_token = access_token
            user.github_username = gh_user["login"]
            user.github_avatar_url = gh_user.get("avatar_url", "")
            logger.info(f"User {gh_user['login']} logged in (existing)")
        else:
            # New user
            user = User(
                github_id=gh_user["id"],
                github_username=gh_user["login"],
                github_avatar_url=gh_user.get("avatar_url", ""),
                github_token=access_token,
            )
            db.add(user)
            logger.info(f"User {gh_user['login']} signed up (new)")

        db.commit()
        db.refresh(user)

        # Step 4: Redirect to frontend with user info in URL params
        redirect_url = f"{config.FRONTEND_URL}/auth/success?user_id={user.id}&username={user.github_username}&avatar={user.github_avatar_url}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{config.FRONTEND_URL}/?error=oauth_failed")


@router.post("/github", response_model=UserResponse)
def github_oauth_callback(body: GitHubCodeRequest, db: Session = Depends(get_db)):
    """
    Exchange a GitHub OAuth authorization code for an access token.
    Creates or updates the user in our database.
    Returns user info (the frontend stores user_id for subsequent requests).
    """
    # Step 1: Exchange code for access token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": config.GITHUB_CLIENT_ID,
            "client_secret": config.GITHUB_CLIENT_SECRET,
            "code": body.code,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="GitHub OAuth token exchange failed")

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        error = token_data.get("error_description", "Unknown error")
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

    # Step 2: Get user info from GitHub
    user_response = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )

    if user_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")

    gh_user = user_response.json()

    # Step 3: Upsert user in database
    user = db.query(User).filter(User.github_id == gh_user["id"]).first()

    if user:
        # Existing user — update token (might have re-authorized with new scopes)
        user.github_token = access_token
        user.github_username = gh_user["login"]
        user.github_avatar_url = gh_user.get("avatar_url", "")
        logger.info(f"User {gh_user['login']} logged in (existing)")
    else:
        # New user
        user = User(
            github_id=gh_user["id"],
            github_username=gh_user["login"],
            github_avatar_url=gh_user.get("avatar_url", ""),
            github_token=access_token,
        )
        db.add(user)
        logger.info(f"User {gh_user['login']} signed up (new)")

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
    )


@router.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return user info by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
    )

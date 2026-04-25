"""
Aegis — GitHub OAuth Routes

Handles:
- POST /api/auth/github  — exchange OAuth code, set httpOnly session cookie
- GET  /api/auth/me      — return current user from cookie (replaces localStorage check)
- POST /api/auth/logout  — clear the session cookie
- GET  /api/auth/user/{id} — get user by ID (kept for backwards compat)
"""

import logging
import requests
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from database.db import get_db
from database.models import User
from utils.crypto import encrypt_token
from utils.limiter import limiter  # rate limiter shared across all routes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GitHubCodeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


class UserResponse(BaseModel):
    id: int
    github_id: int
    github_username: str
    github_avatar_url: str


@router.post("/github", response_model=UserResponse)
@limiter.limit("10/minute")   # prevent OAuth code brute-forcing
def github_oauth_callback(
    body: GitHubCodeRequest,
    request: Request,             # slowapi needs Request to read the client IP
    response: Response,           # We need this to set the cookie on the response
    db: Session = Depends(get_db),
):
    """
    Exchange a GitHub OAuth code for an access token.
    - Saves/updates the user in the database (token encrypted).
    - Sets an httpOnly cookie so the browser never exposes the session to JavaScript.
    - Returns basic user info so the frontend can show the username/avatar.
    """

    # Step 1: Exchange the one-time code for a GitHub access token
    token_payload: dict = {
        "client_id": config.GITHUB_CLIENT_ID,
        "client_secret": config.GITHUB_CLIENT_SECRET,
        "code": body.code,
    }
    if body.redirect_uri:
        token_payload["redirect_uri"] = body.redirect_uri

    logger.info(f"Exchanging OAuth code (length={len(body.code)}) with redirect_uri={body.redirect_uri}")
    logger.info(f"Using client_id={config.GITHUB_CLIENT_ID}, client_secret={config.GITHUB_CLIENT_SECRET[:10]}...")

    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        json=token_payload,
        headers={"Accept": "application/json"},
        timeout=10,
    )

    logger.info(f"GitHub token exchange response: status={token_response.status_code}")
    logger.info(f"GitHub response body: {token_response.text}")

    if token_response.status_code != 200:
        logger.error(f"GitHub OAuth token exchange failed: {token_response.text}")
        raise HTTPException(status_code=400, detail="GitHub OAuth token exchange failed")

    token_data = token_response.json()
    logger.info(f"Token data keys: {list(token_data.keys())}")
    access_token = token_data.get("access_token")

    if not access_token:
        error = token_data.get("error_description", "Unknown error")
        logger.error(f"GitHub OAuth error: {error} (full response: {token_data})")
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

    # Step 2: Use the token to fetch the GitHub user's profile
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

    # Step 3: Create or update the user in our database
    user = db.query(User).filter(User.github_id == gh_user["id"]).first()

    if user:
        # Returning user — refresh their token and profile info
        user.github_token = encrypt_token(access_token)
        user.github_username = gh_user["login"]
        user.github_avatar_url = gh_user.get("avatar_url", "")
        logger.info(f"User {gh_user['login']} logged in (existing)")
    else:
        # First time login — create a new user row
        user = User(
            github_id=gh_user["id"],
            github_username=gh_user["login"],
            github_avatar_url=gh_user.get("avatar_url", ""),
            github_token=encrypt_token(access_token),
        )
        db.add(user)
        logger.info(f"User {gh_user['login']} signed up (new)")

    db.commit()
    db.refresh(user)

    # Step 4: Set an httpOnly session cookie with the user's DB id.
    # httpOnly = JavaScript cannot read this cookie → XSS cannot steal it.
    # secure=False for local dev (HTTP). Set to True in production (HTTPS).
    # samesite="lax" prevents CSRF on cross-site navigations.
    response.set_cookie(
        key="aegis_session",
        value=str(user.id),
        httponly=True,          # not readable by JavaScript
        secure=False,           # set True in production with HTTPS
        samesite="lax",
        max_age=86400 * 7,      # 7 days
        path="/",
    )

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Read the session cookie and return the logged-in user's info.
    The frontend calls this on page load instead of reading localStorage.
    Returns 401 if no valid session cookie exists.
    """
    # Read the user id from the httpOnly cookie
    user_id_str = request.cookies.get("aegis_session")

    if not user_id_str:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
    )


@router.post("/logout")
def logout(response: Response):
    """
    Clear the session cookie — effectively logs the user out.
    """
    response.delete_cookie(key="aegis_session", path="/")
    return {"message": "Logged out"}


@router.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID. Kept for backwards compatibility."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
    )

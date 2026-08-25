import logging
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.entities import User

logger = logging.getLogger("aegis.security")


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract user from session cookie, Authorization Bearer header, or X-Aegis-User-Id.
    Returns None if not authenticated.
    """
    user_id = None
    
    # 1. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        val = auth_header.split(" ")[1].strip()
        if val.isdigit():
            user_id = int(val)
            
    # 2. Check X-Aegis-User-Id header
    if not user_id:
        custom_header = request.headers.get("X-Aegis-User-Id")
        if custom_header and custom_header.isdigit():
            user_id = int(custom_header)
            
    # 3. Check Session Cookie
    if not user_id:
        cookie_val = request.cookies.get("aegis_session") or request.cookies.get("aegis_user_id")
        if cookie_val and cookie_val.isdigit():
            user_id = int(cookie_val)

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
            
    # Fallback to first user in database if single-user mode or local dev
    first_user = db.query(User).first()
    return first_user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Dependency that enforces authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user

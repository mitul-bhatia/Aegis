"""
Aegis — GitHub App Authentication Module

Generates short-lived App JWTs and installation access tokens for multi-tenant background scanning,
repo cloning, and automated Pull Request creation without requiring Personal Access Tokens (PATs).
"""

import time
import jwt
import requests
import logging
from typing import Optional, Dict, Any
import config

logger = logging.getLogger(__name__)

# Cache for installation tokens: { installation_id: (token, expires_at) }
_TOKEN_CACHE: Dict[int, tuple[str, float]] = {}


def generate_app_jwt() -> str:
    """
    Generate a signed JWT for GitHub App authentication (valid for 10 minutes).
    Uses GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY.
    """
    if not config.GITHUB_APP_ID or not config.GITHUB_APP_PRIVATE_KEY:
        raise ValueError("GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY is not configured")

    now = int(time.time())
    payload = {
        "iat": now - 60,             # Issued at (1 min skew grace)
        "exp": now + (10 * 60),      # Expires in 10 minutes
        "iss": str(config.GITHUB_APP_ID),
    }

    # Fix flattened PEM keys (from env vars with spaces instead of newlines)
    private_key = config.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
    if "\n" not in private_key or len(private_key.split("\n")) <= 3:
        import re
        header_match = re.search(r"(-----BEGIN [^-]+-----)", private_key)
        footer_match = re.search(r"(-----END [^-]+-----)", private_key)
        if header_match and footer_match:
            header = header_match.group(1)
            footer = footer_match.group(1)
            content = private_key[private_key.find(header) + len(header) : private_key.find(footer)]
            content = re.sub(r"\s+", "", content)
            lines = [content[i:i+64] for i in range(0, len(content), 64)]
            private_key = f"{header}\n" + "\n".join(lines) + f"\n{footer}\n"

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded_jwt


def get_installation_access_token(installation_id: int) -> str:
    """
    Fetch (or retrieve from cache) an installation access token for a specific installation ID.
    Tokens expire after 1 hour.
    """
    now = time.time()
    
    # Check cache first
    if installation_id in _TOKEN_CACHE:
        token, expires_at = _TOKEN_CACHE[installation_id]
        if expires_at > now + 300:  # Valid for at least 5 more minutes
            return token

    app_jwt = generate_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.post(url, headers=headers, timeout=10)
    
    if response.status_code != 201:
        logger.error(f"Failed to get installation access token for {installation_id}: {response.text}")
        raise ValueError(f"GitHub App auth error: {response.text}")

    data = response.json()
    token = data["access_token"]
    
    # Cache token until 5 mins before actual expiry
    _TOKEN_CACHE[installation_id] = (token, now + 3300)
    return token

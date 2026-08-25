import time
import re
import logging
from typing import Dict, Tuple, Optional
from jose import jwt
import requests
from backend.app.config import settings

logger = logging.getLogger("aegis.github.auth")

# In-memory cache for installation tokens: { installation_id: (token, expires_at_timestamp) }
_TOKEN_CACHE: Dict[int, Tuple[str, float]] = {}


def generate_app_jwt() -> str:
    """
    Generate a signed RS256 JWT for GitHub App authentication (valid for 10 minutes).
    Uses settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY.
    """
    if not settings.GITHUB_APP_ID or not settings.GITHUB_APP_PRIVATE_KEY:
        raise ValueError("GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY is not configured")

    now = int(time.time())
    payload = {
        "iat": now - 60,             # 1 minute clock drift tolerance
        "exp": now + (10 * 60),      # Expires in 10 minutes
        "iss": str(settings.GITHUB_APP_ID),
    }

    # Standardize PEM key formatting
    private_key_raw = settings.GITHUB_APP_PRIVATE_KEY
    header_match = re.search(r"(-----BEGIN [^-]+-----)", private_key_raw)
    footer_match = re.search(r"(-----END [^-]+-----)", private_key_raw)

    if header_match and footer_match:
        header = header_match.group(1)
        footer = footer_match.group(1)
        content = private_key_raw[private_key_raw.find(header) + len(header) : private_key_raw.find(footer)]
        content = re.sub(r"[\s\"']+", "", content)
        lines = [content[i : i + 64] for i in range(0, len(content), 64)]
        private_key = f"{header}\n" + "\n".join(lines) + f"\n{footer}\n"
    else:
        private_key = private_key_raw.replace("\\n", "\n").strip("\"'")

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded_jwt


def get_installation_access_token(installation_id: int) -> str:
    """
    Fetch an installation access token from GitHub (or return valid cached token).
    Tokens expire after 1 hour; we cache until 5 minutes before expiration.
    """
    now = time.time()

    if installation_id in _TOKEN_CACHE:
        token, expires_at = _TOKEN_CACHE[installation_id]
        if expires_at > now + 300:
            return token

    app_jwt = generate_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.post(url, headers=headers, timeout=15)
    if resp.status_code != 201:
        logger.error(f"Failed to get installation access token for {installation_id}: {resp.text}")
        raise ValueError(f"GitHub App auth error ({resp.status_code}): {resp.text}")

    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        raise ValueError(f"Invalid token response from GitHub: {data}")

    # Cache for 55 minutes
    _TOKEN_CACHE[installation_id] = (token, now + 3300)
    return token

"""
Aegis — Token Encryption Utility

GitHub tokens are sensitive. If the database leaks, plaintext tokens
give attackers full access to every user's GitHub account.

We use Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The key lives in the .env file — never in the database or code.

Usage:
    from utils.crypto import encrypt_token, decrypt_token

    # When saving a token to the DB:
    user.github_token = encrypt_token(raw_token)

    # When reading a token from the DB to use it:
    raw_token = decrypt_token(user.github_token)
"""

import logging
from cryptography.fernet import Fernet, InvalidToken
import config

logger = logging.getLogger(__name__)

# Create the Fernet cipher once at import time.
# If FERNET_KEY is missing (e.g. local dev without .env), we fall back to
# storing tokens as plaintext — a warning is logged so you know.
_fernet = None
if config.FERNET_KEY:
    try:
        _fernet = Fernet(config.FERNET_KEY.encode())
    except Exception as e:
        logger.error(f"Invalid FERNET_KEY in .env — tokens will NOT be encrypted: {e}")
else:
    logger.warning("FERNET_KEY not set — GitHub tokens stored as plaintext. Set it in .env!")


def encrypt_token(token: str) -> str:
    """
    Encrypt a GitHub token before storing it in the database.

    Returns the encrypted token as a string (starts with 'gAAAAA...').
    If no FERNET_KEY is configured, returns the token unchanged.
    """
    if not _fernet:
        return token  # No key configured — store as-is (dev only)
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(stored_token: str) -> str:
    """
    Decrypt a GitHub token read from the database.

    Handles two cases gracefully:
    1. Encrypted token (normal case after Task 1.2)
    2. Plaintext token (legacy rows before encryption was added)

    If no FERNET_KEY is configured, returns the token unchanged.
    """
    if not _fernet:
        return stored_token  # No key — return as-is

    try:
        return _fernet.decrypt(stored_token.encode()).decode()
    except (InvalidToken, Exception):
        # Token is probably a legacy plaintext token — return it as-is.
        # This lets old accounts keep working after we add encryption.
        logger.debug("Token appears to be unencrypted (legacy) — returning as-is")
        return stored_token

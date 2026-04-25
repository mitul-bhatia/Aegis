"""
Aegis — Shared Rate Limiter

A single Limiter instance shared across all route files.
main.py attaches this to app.state so slowapi can find it.
Route files import it to apply @limiter.limit() decorators.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function: rate limit per client IP address
limiter = Limiter(key_func=get_remote_address)

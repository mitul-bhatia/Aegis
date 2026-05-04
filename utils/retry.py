"""
Aegis — Retry Logic with Exponential Backoff

Provides retry decorators for API calls with intelligent backoff.
"""

import logging
import time
import functools
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None,
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff (2.0 = double each time)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        def call_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def is_rate_limit_error(exception: Exception) -> bool:
    """
    Check if an exception is a rate limit error.
    
    Handles various rate limit error formats from different APIs.
    """
    error_str = str(exception).lower()
    return any([
        "429" in str(exception),
        "rate limit" in error_str,
        "too many requests" in error_str,
        "quota exceeded" in error_str,
    ])


def is_transient_error(exception: Exception) -> bool:
    """
    Check if an exception is likely transient and worth retrying.
    
    Returns True for network errors, timeouts, and temporary server issues.
    """
    error_str = str(exception).lower()
    
    # Network and timeout errors
    if any(isinstance(exception, exc_type) for exc_type in [
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        ConnectionRefusedError,
        ConnectionAbortedError,
    ]):
        return True
    
    # HTTP status codes that are transient
    transient_codes = ["500", "502", "503", "504", "408"]
    if any(code in str(exception) for code in transient_codes):
        return True
    
    # Common transient error messages
    transient_messages = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "try again",
    ]
    return any(msg in error_str for msg in transient_messages)


class RetryableError(Exception):
    """Exception that should trigger a retry"""
    pass


class NonRetryableError(Exception):
    """Exception that should NOT trigger a retry"""
    pass

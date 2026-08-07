"""
Aegis — Redis Cache Layer

Provides caching for expensive operations like RAG queries and API responses.
"""

import json
import logging
import os
from typing import Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Redis client (optional - gracefully degrades if not available)
try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if REDIS_URL.startswith("rediss://"):
        redis_client = redis.from_url(REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
    else:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis cache connected")
except Exception as e:
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning(f"Redis not available - caching disabled: {e}")


import inspect

def cache_result(key_prefix: str, ttl: int = 3600):
    """
    Decorator to cache function results in Redis (supports sync & async functions).
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds (default 1 hour)
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not REDIS_AVAILABLE:
                    return await func(*args, **kwargs)
                
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                try:
                    cached = redis_client.get(cache_key)
                    if cached:
                        logger.debug(f"Cache hit: {cache_key}")
                        return json.loads(cached)
                    
                    result = await func(*args, **kwargs)
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    logger.debug(f"Cache set: {cache_key}")
                    return result
                except Exception as e:
                    logger.warning(f"Cache error: {e}")
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not REDIS_AVAILABLE:
                    return func(*args, **kwargs)
                
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                try:
                    cached = redis_client.get(cache_key)
                    if cached:
                        logger.debug(f"Cache hit: {cache_key}")
                        return json.loads(cached)
                    
                    result = func(*args, **kwargs)
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    logger.debug(f"Cache set: {cache_key}")
                    return result
                except Exception as e:
                    logger.warning(f"Cache error: {e}")
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidate all cache keys matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "repo_scan:*")
    """
    if not REDIS_AVAILABLE:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")


def get_cache(key: str) -> Optional[Any]:
    """Get value from cache."""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


def set_cache(key: str, value: Any, ttl: int = 3600):
    """Set value in cache."""
    if not REDIS_AVAILABLE:
        return
    
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache set error: {e}")

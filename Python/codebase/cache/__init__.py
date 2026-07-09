"""Cache module for query result caching"""
import os
import logging
from typing import Optional

from .base import BaseCache
from .redis_cache import RedisCache
from .memory_cache import MemoryCache

logger = logging.getLogger(__name__)

# Global cache instance
_cache_instance: Optional[BaseCache] = None


def get_cache() -> Optional[BaseCache]:
    """Get the global cache instance"""
    return _cache_instance


def set_cache(cache: BaseCache):
    """Set the global cache instance"""
    global _cache_instance
    _cache_instance = cache


async def create_cache_from_env() -> BaseCache:
    """Create cache instance from environment variables"""
    cache_type = os.getenv("CACHE_TYPE", "memory").lower()

    if cache_type == "redis":
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD")
        cache_ttl = int(os.getenv("CACHE_TTL", "3600"))

        cache = RedisCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            default_ttl=cache_ttl
        )

        # Test connection
        if await cache.health_check():
            logger.info(f"Redis cache initialized: {redis_host}:{redis_port}")
            set_cache(cache)
            return cache
        else:
            logger.warning("Redis not available, falling back to memory cache")
            cache = MemoryCache(default_ttl=cache_ttl)
            set_cache(cache)
            return cache
    else:
        cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))
        cache = MemoryCache(default_ttl=cache_ttl, max_size=max_size)
        logger.info(f"Memory cache initialized (TTL: {cache_ttl}s, max: {max_size})")
        set_cache(cache)
        return cache


__all__ = [
    "BaseCache",
    "RedisCache",
    "MemoryCache",
    "get_cache",
    "set_cache",
    "create_cache_from_env"
]

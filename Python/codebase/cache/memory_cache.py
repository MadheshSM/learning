"""In-memory cache implementation (for development/fallback)"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple, List

from .base import BaseCache

logger = logging.getLogger(__name__)


class MemoryCache(BaseCache):
    """In-memory cache implementation with TTL support"""

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        # key -> (value, expiry_time, created_time)
        self._cache: Dict[str, Tuple[Any, float, float]] = {}
        self._lock = asyncio.Lock()

    async def _cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired_keys = [
            key for key, (_, expiry, _) in self._cache.items()
            if expiry < now
        ]
        for key in expired_keys:
            del self._cache[key]

    async def _evict_if_needed(self):
        """Evict oldest entries if cache is full"""
        if len(self._cache) >= self.max_size:
            # Remove 10% of oldest entries (by expiry time)
            items = sorted(self._cache.items(), key=lambda x: x[1][1])
            to_remove = max(1, len(items) // 10)
            for key, _ in items[:to_remove]:
                del self._cache[key]

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        async with self._lock:
            await self._cleanup_expired()

            if key in self._cache:
                value, expiry, _ = self._cache[key]
                if expiry > time.time():
                    logger.debug(f"Cache HIT: {key}")
                    return value
                else:
                    del self._cache[key]

            logger.debug(f"Cache MISS: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache with TTL"""
        try:
            async with self._lock:
                await self._evict_if_needed()

                ttl = ttl or self.default_ttl
                now = time.time()
                expiry = now + ttl
                self._cache[key] = (value, expiry, now)
                logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
                return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from memory cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache CLEAR: deleted {count} keys")
            return True

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        async with self._lock:
            if key in self._cache:
                _, expiry, _ = self._cache[key]
                if expiry > time.time():
                    return True
                else:
                    del self._cache[key]
            return False

    async def get_ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key in seconds"""
        async with self._lock:
            if key in self._cache:
                _, expiry, _ = self._cache[key]
                remaining = expiry - time.time()
                if remaining > 0:
                    return remaining
                else:
                    del self._cache[key]
            return None

    async def refresh(self, key: str, ttl: Optional[int] = None) -> bool:
        """Refresh/extend the TTL of an existing key"""
        async with self._lock:
            if key in self._cache:
                value, old_expiry, created = self._cache[key]
                if old_expiry > time.time():
                    ttl = ttl or self.default_ttl
                    new_expiry = time.time() + ttl
                    self._cache[key] = (value, new_expiry, created)
                    logger.debug(f"Cache REFRESH: {key} (new TTL: {ttl}s)")
                    return True
                else:
                    del self._cache[key]
            return False

    async def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern"""
        async with self._lock:
            await self._cleanup_expired()
            keys = list(self._cache.keys())
            if pattern:
                # Simple wildcard matching
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
            return keys

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            await self._cleanup_expired()
            now = time.time()

            # Calculate stats
            entries = []
            total_ttl = 0
            for key, (_, expiry, created) in self._cache.items():
                remaining = expiry - now
                if remaining > 0:
                    entries.append({
                        "key": key,
                        "ttl_remaining": round(remaining, 1),
                        "age": round(now - created, 1)
                    })
                    total_ttl += remaining

            avg_ttl = total_ttl / len(entries) if entries else 0

            return {
                "type": "memory",
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "avg_ttl_remaining": round(avg_ttl, 1),
                "entries": entries
            }

    async def health_check(self) -> bool:
        """Memory cache is always healthy"""
        return True

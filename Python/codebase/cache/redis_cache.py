"""Redis cache implementation"""
import json
import logging
from typing import Any, Optional, List, Dict

import redis.asyncio as redis

from .base import BaseCache

logger = logging.getLogger(__name__)


class RedisCache(BaseCache):
    """Redis-based cache implementation"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,  # 1 hour default
        prefix: str = "acc_cache"
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
        return self._client

    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            client = await self._get_client()
            value = await client.get(self._prefixed_key(key))
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except redis.RedisError as e:
            logger.error(f"Redis get error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with TTL"""
        try:
            client = await self._get_client()
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            await client.setex(
                self._prefixed_key(key),
                ttl,
                serialized
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis set error: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"JSON encode error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            client = await self._get_client()
            result = await client.delete(self._prefixed_key(key))
            logger.debug(f"Cache DELETE: {key} (deleted: {result})")
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache entries with prefix"""
        try:
            client = await self._get_client()
            pattern = f"{self.prefix}:*"
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await client.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"Cache CLEAR: deleted {deleted} keys")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis clear error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            client = await self._get_client()
            return await client.exists(self._prefixed_key(key)) > 0
        except redis.RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key in seconds"""
        try:
            client = await self._get_client()
            ttl = await client.ttl(self._prefixed_key(key))
            if ttl > 0:
                return float(ttl)
            return None  # Key doesn't exist or has no TTL
        except redis.RedisError as e:
            logger.error(f"Redis TTL error: {e}")
            return None

    async def refresh(self, key: str, ttl: Optional[int] = None) -> bool:
        """Refresh/extend the TTL of an existing key"""
        try:
            client = await self._get_client()
            prefixed_key = self._prefixed_key(key)

            # Check if key exists
            if not await client.exists(prefixed_key):
                return False

            ttl = ttl or self.default_ttl
            result = await client.expire(prefixed_key, ttl)
            if result:
                logger.debug(f"Cache REFRESH: {key} (new TTL: {ttl}s)")
            return result
        except redis.RedisError as e:
            logger.error(f"Redis refresh error: {e}")
            return False

    async def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern"""
        try:
            client = await self._get_client()
            if pattern:
                search_pattern = f"{self.prefix}:{pattern}"
            else:
                search_pattern = f"{self.prefix}:*"

            keys = []
            cursor = 0
            while True:
                cursor, batch = await client.scan(cursor, match=search_pattern, count=100)
                # Remove prefix from keys
                for key in batch:
                    if key.startswith(f"{self.prefix}:"):
                        keys.append(key[len(self.prefix) + 1:])
                    else:
                        keys.append(key)
                if cursor == 0:
                    break
            return keys
        except redis.RedisError as e:
            logger.error(f"Redis get_keys error: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            client = await self._get_client()

            # Get all keys with prefix
            keys = await self.get_keys()

            entries = []
            total_ttl = 0
            for key in keys:
                ttl = await self.get_ttl(key)
                if ttl is not None:
                    entries.append({
                        "key": key,
                        "ttl_remaining": round(ttl, 1)
                    })
                    total_ttl += ttl

            avg_ttl = total_ttl / len(entries) if entries else 0

            # Get Redis server info
            info = await client.info("memory")

            return {
                "type": "redis",
                "size": len(entries),
                "default_ttl": self.default_ttl,
                "avg_ttl_remaining": round(avg_ttl, 1),
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "entries": entries
            }
        except redis.RedisError as e:
            logger.error(f"Redis stats error: {e}")
            return {
                "type": "redis",
                "size": 0,
                "error": str(e)
            }

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Check if Redis is available"""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except redis.RedisError:
            return False

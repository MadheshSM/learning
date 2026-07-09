"""Base cache interface for query caching"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
import hashlib
import re
import json
import time


class CacheEntry:
    """Represents a cache entry with metadata"""
    def __init__(self, key: str, value: Any, ttl_remaining: float, created_at: Optional[float] = None):
        self.key = key
        self.value = value
        self.ttl_remaining = ttl_remaining
        self.created_at = created_at or time.time()

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "ttl_remaining": round(self.ttl_remaining, 1),
            "created_at": self.created_at
        }


class BaseCache(ABC):
    """Abstract base class for cache implementations"""

    def generate_key(self, query: str, project_id: Optional[str] = None) -> str:
        """Generate a cache key from query and project_id"""
        cleaned = re.sub(r"[.!?,;:]+$", "", query.lower().strip())
        key_data = {
            "query": cleaned,
            "project_id": project_id
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"acc_query:{hashlib.sha256(key_string.encode()).hexdigest()[:32]}"

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key in seconds. Returns None if key doesn't exist."""
        pass

    @abstractmethod
    async def refresh(self, key: str, ttl: Optional[int] = None) -> bool:
        """Refresh/extend the TTL of an existing key. Returns False if key doesn't exist."""
        pass

    @abstractmethod
    async def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """Get all cache keys, optionally filtered by pattern"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass

    async def get_query_result(self, query: str, project_id: Optional[str] = None) -> Optional[Any]:
        """Get cached query result"""
        key = self.generate_key(query, project_id)
        return await self.get(key)

    async def set_query_result(
        self,
        query: str,
        result: Any,
        project_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache a query result"""
        key = self.generate_key(query, project_id)
        return await self.set(key, result, ttl)

    async def invalidate_query(self, query: str, project_id: Optional[str] = None) -> bool:
        """Invalidate a cached query"""
        key = self.generate_key(query, project_id)
        return await self.delete(key)

    async def refresh_query(self, query: str, project_id: Optional[str] = None, ttl: Optional[int] = None) -> bool:
        """Refresh TTL for a cached query"""
        key = self.generate_key(query, project_id)
        return await self.refresh(key, ttl)

    async def get_query_ttl(self, query: str, project_id: Optional[str] = None) -> Optional[float]:
        """Get remaining TTL for a cached query"""
        key = self.generate_key(query, project_id)
        return await self.get_ttl(key)

    async def invalidate_project(self, project_id: str) -> int:
        """Invalidate all cache entries for a specific project. Returns count of deleted entries."""
        # This is a default implementation that scans all keys
        # Subclasses can override for more efficient implementations
        keys = await self.get_keys()
        deleted = 0
        for key in keys:
            # Check if this key belongs to the project (by checking stored value)
            value = await self.get(key)
            if value and isinstance(value, dict):
                # Check if the cached result has routing info with project context
                routing = value.get('routing', {})
                if routing and project_id in str(routing):
                    if await self.delete(key):
                        deleted += 1
        return deleted

    async def get_all_entries(self) -> List[Dict]:
        """Get metadata for all cache entries"""
        keys = await self.get_keys()
        entries = []
        for key in keys:
            ttl = await self.get_ttl(key)
            if ttl is not None:
                entries.append({
                    "key": key,
                    "ttl_remaining": round(ttl, 1)
                })
        return entries

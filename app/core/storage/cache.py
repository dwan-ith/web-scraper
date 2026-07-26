"""
Redis Cache Layer
"""
import logging
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

_cache: Optional["Cache"] = None

class Cache:
    def __init__(self, client: aioredis.Redis):
        self.client = client

    async def get(self, key: str) -> Optional[str]:
        try:
            value = await self.client.get(key)
            return value.decode("utf-8") if value else None
        except Exception as e:
            logger.warning(f"Cache GET failed for {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        try:
            await self.client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Cache SET failed for {key}: {e}")

    async def delete(self, key: str):
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache DELETE failed for {key}: {e}")

async def init_cache():
    global _cache
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=False)
        await client.ping()
        _cache = Cache(client)
        logger.info("✅ Redis cache connected")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}). Using in-memory fallback.")
        _cache = InMemoryCache()

async def get_cache() -> Cache:
    global _cache
    if _cache is None:
        await init_cache()
    return _cache

class InMemoryCache:
    """Fallback in-memory cache when Redis is not available."""
    def __init__(self):
        self._store = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600):
        self._store[key] = value

    async def delete(self, key: str):
        self._store.pop(key, None)

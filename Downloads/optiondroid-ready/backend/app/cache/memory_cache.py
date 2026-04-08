"""
Thread-safe in-memory TTL cache.
Keys expire after settings.cache_ttl seconds.
Replace with Redis adapter if you need distributed caching.
"""
import time
import asyncio
import logging
from typing import Any, Optional, Tuple
from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE_MAXSIZE = 256

_store: TTLCache = TTLCache(maxsize=_CACHE_MAXSIZE, ttl=settings.cache_ttl)
_lock = asyncio.Lock()


async def get(key: str) -> Optional[Any]:
    async with _lock:
        value = _store.get(key)
        if value is not None:
            logger.debug(f"Cache HIT: {key}")
        return value


async def set(key: str, value: Any) -> None:
    async with _lock:
        _store[key] = value
        logger.debug(f"Cache SET: {key}")


async def invalidate(key: str) -> None:
    async with _lock:
        _store.pop(key, None)


async def clear() -> None:
    async with _lock:
        _store.clear()
        logger.info("Cache cleared.")


def cache_key(*parts) -> str:
    return ":".join(str(p).lower() for p in parts)

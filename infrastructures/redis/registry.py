from typing import Optional

import redis.asyncio as aioredis

from commons.config import get_configs

_redis: Optional[aioredis.Redis] = None


def register_redis() -> aioredis.Redis:
    """Create and register the global async Redis client from application config."""
    global _redis
    cfg = get_configs()
    _redis = aioredis.from_url(
        cfg.CACHE_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis


def get_redis_client() -> aioredis.Redis:
    """Return the active Redis client, raising if not yet initialised."""
    if _redis is None:
        raise RuntimeError(
            "Redis client is not initialised — register_redis() must be called "
            "from the lifespan before any cache operation is requested."
        )
    return _redis


async def close_redis() -> None:
    """Close the active Redis connection and reset the global client."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None

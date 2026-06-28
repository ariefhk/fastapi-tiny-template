from typing import Optional, cast

from commons.config import get_configs
from infrastructures.redis.registry import get_redis_client


async def get_cache(key: str) -> Optional[str]:
    client = get_redis_client()
    return cast(Optional[str], await client.get(key))


async def set_cache(key: str, value: str, ttl: int | None = None) -> None:
    client = get_redis_client()
    cfg = get_configs()
    ttl = ttl or cfg.CACHE_DEFAULT_TTL
    await client.set(key, value, ex=ttl)


async def delete_cache_pattern(pattern: str) -> int:
    """Delete all keys matching a glob pattern. Returns number of keys deleted."""
    client = get_redis_client()
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = await client.scan(cursor, match=pattern, count=100)
        if keys:
            deleted += await client.delete(*keys)
        if cursor == 0:
            break
    return deleted


async def delete_cache_key(key: str) -> bool:
    """Delete an exact key. Returns True if the key existed."""
    client = get_redis_client()
    result = await client.delete(key)
    return result > 0


async def get_list_cache_keys(pattern: str = "*") -> list[dict]:
    """Return all keys matching pattern with their remaining TTL in seconds.

    TTL of -1 means the key has no expiry.
    """
    client = get_redis_client()
    cursor = 0
    keys: list[str] = []
    while True:
        cursor, batch = await client.scan(cursor, match=pattern, count=100)
        keys.extend(cast(list[str], batch))
        if cursor == 0:
            break

    result = []
    for key in sorted(keys):
        ttl = await client.ttl(key)
        result.append({"key": key, "ttl": ttl})
    return result

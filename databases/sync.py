"""
Drop all tables and recreate from current models.
"""

import asyncio

import redis.asyncio as aioredis
from sqlalchemy import text

import models  # noqa: F401 — registers all models with Base.metadata
from commons.config import get_configs
from databases.base import Base
from databases.registry import register_database


async def force_sync() -> None:
    cfg = get_configs()

    if cfg.ENVIRONMENT != "dev":
        print(
            "WARNING: force-sync is running in a non-dev environment. All data will be destroyed."
        )

    db_conn = register_database()

    async with db_conn.begin() as conn:
        print("Dropping schema with CASCADE...")
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        print("Recreating tables from current models...")
        await conn.run_sync(Base.metadata.create_all)

    await db_conn.dispose()
    print("Done — database is now in sync with current models.")

    print("Flushing Redis cache...")
    try:
        if cfg.CACHE_ENABLED and cfg.CACHE_URL:
            redis_client = aioredis.from_url(cfg.CACHE_URL, decode_responses=False)
            await redis_client.flushdb()
            await redis_client.aclose()
            print("Done — Redis cache flushed.")
        else:
            print("Cache not enabled, skipping.")
    except Exception as err:
        print(f"WARNING: Redis flush failed: {err}")


if __name__ == "__main__":
    asyncio.run(force_sync())

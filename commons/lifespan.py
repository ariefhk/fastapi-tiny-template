from contextlib import asynccontextmanager

from fastapi import FastAPI

from commons.config import get_configs
from databases.registry import close_database, register_database
from infrastructures.redis.registry import close_redis, register_redis
from loggers.helper import get_logger

logger = get_logger(__name__)
_cfg = get_configs()


async def _startup(app: FastAPI) -> None:
    """Initialise external connections on application startup."""
    if _cfg.DB_ENABLED:
        register_database()
    else:
        logger.info("database: DISABLED — set DB_ENABLED=true in .env to enable")

    if _cfg.CACHE_ENABLED:
        register_redis()
        logger.info("cache: connected to %s", _cfg.CACHE_URL)
    else:
        logger.info("cache: DISABLED — set CACHE_ENABLED=true in .env to enable")


async def _shutdown(app: FastAPI) -> None:
    """Tear down external connections on application shutdown."""
    if _cfg.DB_ENABLED:
        await close_database()

    if _cfg.CACHE_ENABLED:
        await close_redis()
        logger.info("cache: connection closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — runs startup tasks before yield, shutdown tasks after."""
    await _startup(app)
    yield
    await _shutdown(app)

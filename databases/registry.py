from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from commons.config import get_configs
from commons.tunnel import close_ssh_tunnels, open_ssh_tunnels
from databases.helper import build_database_url
from loggers.helper import get_logger

if TYPE_CHECKING:
    from sshtunnel import SSHTunnelForwarder

logger = get_logger(__name__)
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def register_database(pg_tunnel: SSHTunnelForwarder | None = None) -> AsyncEngine:
    """Create the global async engine and session factory from application config.

    Opens SSH tunnel(s) from config when ``DB_SSH_ENABLED`` is true, unless
    ``pg_tunnel`` is passed explicitly (useful for tests). Idempotent — disposes
    any existing engine before rebuilding so re-initialisation doesn't leak connections.
    """
    global engine, AsyncSessionLocal

    cfg = get_configs()
    echo_sql = cfg.ENVIRONMENT in ("dev", "dev.tunnel")

    active_tunnel = pg_tunnel if pg_tunnel is not None else open_ssh_tunnels()

    if active_tunnel is not None:
        host = "127.0.0.1"
        port = active_tunnel.local_bind_port
    else:
        host = cfg.DB_HOST
        port = cfg.DB_PORT

    database_url = build_database_url(
        host=host,
        port=port,
        name=cfg.DB_NAME,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
    )

    connect_args: dict[str, Any] = {}
    if "postgresql" in database_url:
        connect_args["server_settings"] = {
            "statement_timeout": "30000",
            "idle_in_transaction_session_timeout": "60000",
        }

    if engine is not None:
        try:
            engine.sync_engine.dispose()
        except Exception:
            pass

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        echo=echo_sql,
        connect_args=connect_args,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine


async def close_database() -> None:
    """Dispose the engine connection pool and close any open SSH tunnels."""
    global engine

    if engine is not None:
        await engine.dispose()
        engine = None
        logger.info("database: connection pool disposed")

    close_ssh_tunnels()

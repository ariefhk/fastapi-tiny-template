import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import models  # noqa: F401 — import all models so autogenerate can detect them
from commons.config import get_configs
from commons.tunnel import close_ssh_tunnels, open_ssh_tunnels
from databases.base import Base
from databases.helper import build_database_url

if TYPE_CHECKING:
    from sshtunnel import SSHTunnelForwarder

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url(tunnel: SSHTunnelForwarder | None = None) -> str:
    cfg = get_configs()
    if tunnel is not None:
        host, port = "127.0.0.1", tunnel.local_bind_port
    else:
        host, port = cfg.DB_HOST, cfg.DB_PORT
    return build_database_url(
        host=host,
        port=port,
        name=cfg.DB_NAME,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
    )


def run_migrations_offline() -> None:
    tunnel = open_ssh_tunnels()
    try:
        context.configure(
            url=_get_url(tunnel),
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    finally:
        close_ssh_tunnels()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    tunnel = open_ssh_tunnels()
    try:
        engine = create_async_engine(_get_url(tunnel))
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await engine.dispose()
    finally:
        close_ssh_tunnels()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

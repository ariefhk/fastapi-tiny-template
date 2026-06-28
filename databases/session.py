from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

import databases.registry as _engine


async def get_db_session() -> AsyncSession:
    if _engine.AsyncSessionLocal is None:
        raise RuntimeError(
            "Database engine not initialised — register_database() must be called "
            "from the lifespan before any DB session is requested."
        )
    return _engine.AsyncSessionLocal()


async def db_session_deps() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a DB session, commits on success, rolls back on error."""
    session = await get_db_session()

    async with session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_session_ctx() -> AsyncIterator[AsyncSession]:
    """Context manager for a DB session outside a FastAPI request (jobs, scripts, seeds).

    Same commit/rollback semantics as ``get_db``.

    Usage::

        async with db_session() as session:
            repository = ItemRepository(session)
            service = ItemService(session=session, item_repository=repository)
            await service.do_work()
    """
    session = await get_db_session()
    async with session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

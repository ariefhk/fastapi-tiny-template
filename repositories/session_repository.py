import uuid
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.session_model import SessionModel
from schemas.requests.session_request import SessionFilterRequest


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for sessions."""
        return select(SessionModel)

    def _apply_filters(self, stmt, filters: SessionFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.user_id is not None:
            conditions.append(SessionModel.user_id == filters.user_id)
        if filters.active_company_id is not None:
            conditions.append(SessionModel.active_company_id == filters.active_company_id)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> SessionModel | None:
        """Return a single session by primary key, or None if not found."""
        stmt = self._base_query().where(SessionModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> SessionModel | None:
        """Return a single session by refresh token hash, or None if not found."""
        stmt = self._base_query().where(
            SessionModel.refresh_token_hash == refresh_token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: SessionFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[SessionModel], int]:
        """Return a page of sessions matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(SessionModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(SessionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def delete_by_user_id(self, user_id: uuid.UUID) -> int:
        """Hard-delete all sessions belonging to *user_id*. Returns the row count."""
        stmt = delete(SessionModel).where(SessionModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def create(
        self,
        user_id: uuid.UUID,
        active_company_id: uuid.UUID | None,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> SessionModel:
        """Stage a new session. Persisted on the next flush/commit."""
        session = SessionModel(
            user_id=user_id,
            active_company_id=active_company_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        self._session.add(session)
        return session

    async def delete(self, session: SessionModel) -> None:
        """Hard-delete a single session."""
        await self._session.delete(session)

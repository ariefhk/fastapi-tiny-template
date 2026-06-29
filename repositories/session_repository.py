import uuid
from datetime import datetime

from sqlalchemy import select
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
            conditions.append(
                SessionModel.active_company_id == filters.active_company_id
            )
        return stmt.where(*conditions)

    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> SessionModel | None:
        """Return a single session by refresh token hash, or None if not found."""
        stmt = self._base_query().where(
            SessionModel.refresh_token_hash == refresh_token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def rotate(
        self, session_row: SessionModel, refresh_token_hash: str, expires_at: datetime
    ) -> SessionModel:
        session_row.refresh_token_hash = refresh_token_hash
        session_row.expires_at = expires_at
        return session_row

    async def set_active_company(
        self, session_row: SessionModel, company_id: uuid.UUID
    ) -> SessionModel:
        session_row.active_company_id = company_id
        return session_row

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

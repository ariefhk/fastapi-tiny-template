import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.session_model import SessionModel
from schemas.requests.session_request import (
    SessionCreateRequest,
    SessionFilterRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.session_response import SessionResponse
from services.activity_log_service import ActivityLogMixin


class SessionService(ActivityLogMixin):
    _TABLE = SessionModel.__tablename__
    _CACHE_PREFIX = _TABLE

    def __init__(
        self,
        uow: UnitOfWork,
        actor_id: UUID | None = None,
        company_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._uow = uow
        self._actor_id = actor_id
        self._company_id = company_id
        self._ip_address = ip_address
        self._user_agent = user_agent

    @staticmethod
    def cache_get_by_id_key(session_id: UUID) -> str:
        return f"{SessionService._CACHE_PREFIX}:id={session_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        user_id: UUID | None,
        active_company_id: UUID | None,
    ) -> str:
        return (
            f"{SessionService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":user={user_id}:company={active_company_id}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all session cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{SessionService._CACHE_PREFIX}:*")

    async def _fetch_session(self, id: UUID) -> SessionModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        session = await self._uow.sessions.get_by_id(id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    async def get_by_id(self, id: UUID) -> SessionModel:
        """Return a single session or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return SessionResponse.model_validate_json(cached)  # type: ignore[return-value]

        session = await self._fetch_session(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                SessionResponse.model_validate(session).model_dump_json(),
            )
        return session

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> SessionModel:
        """Return a single session by refresh token hash or raise 404."""
        session = await self._uow.sessions.get_by_refresh_token_hash(refresh_token_hash)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    async def get_all(
        self,
        filters: SessionFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[SessionModel], int]:
        """Return a paginated list of sessions and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            user_id=filters.user_id,
            active_company_id=filters.active_company_id,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [SessionResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.sessions.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [SessionResponse.model_validate(s).model_dump(mode="json") for s in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: SessionCreateRequest) -> SessionModel:
        """Create a session, log the action, and return it with all fields resolved."""
        session = await self._uow.sessions.create(
            user_id=body.user_id,
            active_company_id=body.active_company_id,
            refresh_token_hash=body.refresh_token_hash,
            expires_at=body.expires_at,
        )
        await self._uow.flush()
        await self._uow.refresh(session)
        after = SessionResponse.model_validate(session).model_dump(mode="json")
        await self._log_activity(session.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return session

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        session = await self._fetch_session(id)
        before = SessionResponse.model_validate(session).model_dump(mode="json")
        await self._uow.sessions.delete(session)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.membership_model import MembershipModel, MembershipStatusEnum
from schemas.requests.membership_request import (
    MembershipCreateRequest,
    MembershipFilterRequest,
    MembershipUpdateRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.membership_response import MembershipResponse
from services.activity_log_service import ActivityLogMixin


class MembershipService(ActivityLogMixin):
    _TABLE = MembershipModel.__tablename__
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
    def cache_get_by_id_key(membership_id: UUID) -> str:
        return f"{MembershipService._CACHE_PREFIX}:id={membership_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        user_id: UUID | None,
        company_id: UUID | None,
        status: MembershipStatusEnum | None,
    ) -> str:
        return (
            f"{MembershipService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":user={user_id}:company={company_id}:status={status}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all membership cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{MembershipService._CACHE_PREFIX}:*")

    async def _fetch_membership(self, id: UUID) -> MembershipModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        membership = await self._uow.memberships.get_by_id(id)
        if membership is None:
            raise HTTPException(status_code=404, detail="Membership not found")
        return membership

    async def get_by_id(self, id: UUID) -> MembershipModel:
        """Return a single membership or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return MembershipResponse.model_validate_json(cached)  # type: ignore[return-value]

        membership = await self._fetch_membership(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                MembershipResponse.model_validate(membership).model_dump_json(),
            )
        return membership

    async def get_by_user_and_company(
        self, user_id: UUID, company_id: UUID
    ) -> MembershipModel:
        """Return the membership for a user-company pair or raise 404."""
        membership = await self._uow.memberships.get_by_user_and_company(
            user_id=user_id, company_id=company_id
        )
        if membership is None:
            raise HTTPException(status_code=404, detail="Membership not found")
        return membership

    async def get_all(
        self,
        filters: MembershipFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipModel], int]:
        """Return a paginated list of memberships and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            user_id=filters.user_id,
            company_id=filters.company_id,
            status=filters.status,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [MembershipResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.memberships.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [MembershipResponse.model_validate(m).model_dump(mode="json") for m in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: MembershipCreateRequest) -> MembershipModel:
        """Create a membership, log the action, and return it with all fields resolved."""
        membership = await self._uow.memberships.create(
            user_id=body.user_id,
            company_id=body.company_id,
            status=body.status,
        )
        await self._uow.flush()
        await self._uow.refresh(membership)
        after = MembershipResponse.model_validate(membership).model_dump(mode="json")
        await self._log_activity(membership.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return membership

    async def update(self, id: UUID, body: MembershipUpdateRequest) -> MembershipModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated membership."""
        membership = await self._fetch_membership(id)
        before = MembershipResponse.model_validate(membership).model_dump(mode="json")
        update_data = body.model_dump(exclude_none=True)
        await self._uow.memberships.update(membership, **update_data)
        await self._uow.flush()
        await self._uow.refresh(membership)
        after = MembershipResponse.model_validate(membership).model_dump(mode="json")
        await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
        await self.cache_invalidate()
        return membership

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        membership = await self._fetch_membership(id)
        before = MembershipResponse.model_validate(membership).model_dump(mode="json")
        await self._uow.memberships.delete(membership)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.membership_role_model import MembershipRoleModel
from schemas.requests.membership_role_request import (
    MembershipRoleCreateRequest,
    MembershipRoleFilterRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.membership_role_response import MembershipRoleResponse
from services.activity_log_service import ActivityLogMixin


class MembershipRoleService(ActivityLogMixin):
    _TABLE = MembershipRoleModel.__tablename__
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
    def cache_get_by_id_key(mr_id: UUID) -> str:
        return f"{MembershipRoleService._CACHE_PREFIX}:id={mr_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        membership_id: UUID | None,
        role_id: UUID | None,
    ) -> str:
        return (
            f"{MembershipRoleService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":membership={membership_id}:role={role_id}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all membership role cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{MembershipRoleService._CACHE_PREFIX}:*")

    async def _fetch_membership_role(self, id: UUID) -> MembershipRoleModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        mr = await self._uow.membership_roles.get_by_id(id)
        if mr is None:
            raise HTTPException(status_code=404, detail="Membership role not found")
        return mr

    async def get_by_id(self, id: UUID) -> MembershipRoleModel:
        """Return a single membership role or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return MembershipRoleResponse.model_validate_json(cached)  # type: ignore[return-value]

        mr = await self._fetch_membership_role(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                MembershipRoleResponse.model_validate(mr).model_dump_json(),
            )
        return mr

    async def get_all(
        self,
        filters: MembershipRoleFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipRoleModel], int]:
        """Return a paginated list of membership roles and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            membership_id=filters.membership_id,
            role_id=filters.role_id,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [MembershipRoleResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.membership_roles.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [MembershipRoleResponse.model_validate(m).model_dump(mode="json") for m in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: MembershipRoleCreateRequest) -> MembershipRoleModel:
        """Create a membership role link, log the action, and return it with all fields resolved."""
        mr = await self._uow.membership_roles.create(
            membership_id=body.membership_id,
            role_id=body.role_id,
        )
        await self._uow.flush()
        await self._uow.refresh(mr)
        after = MembershipRoleResponse.model_validate(mr).model_dump(mode="json")
        await self._log_activity(mr.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return mr

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        mr = await self._fetch_membership_role(id)
        before = MembershipRoleResponse.model_validate(mr).model_dump(mode="json")
        await self._uow.membership_roles.delete(mr)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

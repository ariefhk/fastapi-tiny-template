import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.role_model import RoleModel
from schemas.requests.role_request import (
    RoleCreateRequest,
    RoleFilterRequest,
    RoleUpdateRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.role_response import RoleResponse
from services.activity_log_service import ActivityLogMixin


class RoleService(ActivityLogMixin):
    _TABLE = RoleModel.__tablename__
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
    def cache_get_by_id_key(role_id: UUID) -> str:
        return f"{RoleService._CACHE_PREFIX}:id={role_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        company_id: UUID | None,
        name: str | None,
        slug: str | None,
        is_system: bool | None,
    ) -> str:
        return (
            f"{RoleService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":company={company_id}:name={name}:slug={slug}:is_system={is_system}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all role cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{RoleService._CACHE_PREFIX}:*")

    async def _fetch_role(self, id: UUID) -> RoleModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        role = await self._uow.roles.get_by_id(id)
        if role is None:
            raise HTTPException(status_code=404, detail="Role not found")
        return role

    async def get_by_id(self, id: UUID) -> RoleModel:
        """Return a single role or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return RoleResponse.model_validate_json(cached)  # type: ignore[return-value]

        role = await self._fetch_role(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                RoleResponse.model_validate(role).model_dump_json(),
            )
        return role

    async def get_all(
        self,
        filters: RoleFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[RoleModel], int]:
        """Return a paginated list of roles and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            company_id=filters.company_id,
            name=filters.name,
            slug=filters.slug,
            is_system=filters.is_system,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [RoleResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.roles.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [RoleResponse.model_validate(r).model_dump(mode="json") for r in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: RoleCreateRequest) -> RoleModel:
        """Create a role, log the action, and return it with all fields resolved."""
        role = await self._uow.roles.create(
            name=body.name,
            slug=body.slug,
            company_id=body.company_id,
            is_system=body.is_system,
        )
        await self._uow.flush()
        await self._uow.refresh(role)
        after = RoleResponse.model_validate(role).model_dump(mode="json")
        await self._log_activity(role.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return role

    async def update(self, id: UUID, body: RoleUpdateRequest) -> RoleModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated role."""
        role = await self._fetch_role(id)
        before = RoleResponse.model_validate(role).model_dump(mode="json")
        update_data = body.model_dump(exclude_none=True)
        await self._uow.roles.update(role, **update_data)
        await self._uow.flush()
        await self._uow.refresh(role)
        after = RoleResponse.model_validate(role).model_dump(mode="json")
        await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
        await self.cache_invalidate()
        return role

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        role = await self._fetch_role(id)
        before = RoleResponse.model_validate(role).model_dump(mode="json")
        await self._uow.roles.delete(role)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

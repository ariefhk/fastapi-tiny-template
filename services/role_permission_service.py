import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.role_permission_model import RolePermissionModel
from schemas.requests.role_permission_request import (
    RolePermissionCreateRequest,
    RolePermissionFilterRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.role_permission_response import RolePermissionResponse
from services.activity_log_service import ActivityLogMixin


class RolePermissionService(ActivityLogMixin):
    _TABLE = RolePermissionModel.__tablename__
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
    def cache_get_by_id_key(rp_id: UUID) -> str:
        return f"{RolePermissionService._CACHE_PREFIX}:id={rp_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        role_id: UUID | None,
        permission_id: UUID | None,
    ) -> str:
        return (
            f"{RolePermissionService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":role={role_id}:permission={permission_id}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all role permission cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{RolePermissionService._CACHE_PREFIX}:*")

    async def _fetch_role_permission(self, id: UUID) -> RolePermissionModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        rp = await self._uow.role_permissions.get_by_id(id)
        if rp is None:
            raise HTTPException(status_code=404, detail="Role permission not found")
        return rp

    async def get_by_id(self, id: UUID) -> RolePermissionModel:
        """Return a single role permission or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return RolePermissionResponse.model_validate_json(cached)  # type: ignore[return-value]

        rp = await self._fetch_role_permission(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                RolePermissionResponse.model_validate(rp).model_dump_json(),
            )
        return rp

    async def get_all(
        self,
        filters: RolePermissionFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[RolePermissionModel], int]:
        """Return a paginated list of role permissions and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            role_id=filters.role_id,
            permission_id=filters.permission_id,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [RolePermissionResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.role_permissions.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [RolePermissionResponse.model_validate(r).model_dump(mode="json") for r in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: RolePermissionCreateRequest) -> RolePermissionModel:
        """Create a role permission link, log the action, and return it with all fields resolved."""
        rp = await self._uow.role_permissions.create(
            role_id=body.role_id,
            permission_id=body.permission_id,
        )
        await self._uow.flush()
        await self._uow.refresh(rp)
        after = RolePermissionResponse.model_validate(rp).model_dump(mode="json")
        await self._log_activity(rp.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return rp

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        rp = await self._fetch_role_permission(id)
        before = RolePermissionResponse.model_validate(rp).model_dump(mode="json")
        await self._uow.role_permissions.delete(rp)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

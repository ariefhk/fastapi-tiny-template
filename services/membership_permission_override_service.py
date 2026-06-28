import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.membership_permission_override_model import (
    MembershipPermissionOverrideModel,
    OverrideEffectEnum,
)
from schemas.requests.membership_permission_override_request import (
    MembershipPermissionOverrideCreateRequest,
    MembershipPermissionOverrideFilterRequest,
    MembershipPermissionOverrideUpdateRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.membership_permission_override_response import (
    MembershipPermissionOverrideResponse,
)
from services.activity_log_service import ActivityLogMixin


class MembershipPermissionOverrideService(ActivityLogMixin):
    _TABLE = MembershipPermissionOverrideModel.__tablename__
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
    def cache_get_by_id_key(override_id: UUID) -> str:
        return f"{MembershipPermissionOverrideService._CACHE_PREFIX}:id={override_id}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        membership_id: UUID | None,
        permission_id: UUID | None,
        effect: OverrideEffectEnum | None,
    ) -> str:
        return (
            f"{MembershipPermissionOverrideService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":membership={membership_id}:permission={permission_id}:effect={effect}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all permission override cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(
                f"{MembershipPermissionOverrideService._CACHE_PREFIX}:*"
            )

    async def _fetch_override(self, id: UUID) -> MembershipPermissionOverrideModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        override = await self._uow.membership_permission_overrides.get_by_id(id)
        if override is None:
            raise HTTPException(status_code=404, detail="Permission override not found")
        return override

    async def get_by_id(self, id: UUID) -> MembershipPermissionOverrideModel:
        """Return a single permission override or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return MembershipPermissionOverrideResponse.model_validate_json(cached)  # type: ignore[return-value]

        override = await self._fetch_override(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                MembershipPermissionOverrideResponse.model_validate(override).model_dump_json(),
            )
        return override

    async def get_by_membership_and_permission(
        self, membership_id: UUID, permission_id: UUID
    ) -> MembershipPermissionOverrideModel:
        """Return the override for a membership-permission pair or raise 404."""
        override = await self._uow.membership_permission_overrides.get_by_membership_and_permission(
            membership_id=membership_id, permission_id=permission_id
        )
        if override is None:
            raise HTTPException(status_code=404, detail="Permission override not found")
        return override

    async def get_all(
        self,
        filters: MembershipPermissionOverrideFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipPermissionOverrideModel], int]:
        """Return a paginated list of permission overrides and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            membership_id=filters.membership_id,
            permission_id=filters.permission_id,
            effect=filters.effect,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [MembershipPermissionOverrideResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.membership_permission_overrides.get_all(
            filters, page=page, limit=limit
        )

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [
                    MembershipPermissionOverrideResponse.model_validate(o).model_dump(mode="json")
                    for o in items
                ],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(
        self, body: MembershipPermissionOverrideCreateRequest
    ) -> MembershipPermissionOverrideModel:
        """Create a permission override, log the action, and return it with all fields resolved."""
        override = await self._uow.membership_permission_overrides.create(
            membership_id=body.membership_id,
            permission_id=body.permission_id,
            effect=body.effect,
        )
        await self._uow.flush()
        await self._uow.refresh(override)
        after = MembershipPermissionOverrideResponse.model_validate(override).model_dump(mode="json")
        await self._log_activity(override.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return override

    async def update(
        self, id: UUID, body: MembershipPermissionOverrideUpdateRequest
    ) -> MembershipPermissionOverrideModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated override."""
        override = await self._fetch_override(id)
        before = MembershipPermissionOverrideResponse.model_validate(override).model_dump(mode="json")
        update_data = body.model_dump(exclude_none=True)
        await self._uow.membership_permission_overrides.update(override, **update_data)
        await self._uow.flush()
        await self._uow.refresh(override)
        after = MembershipPermissionOverrideResponse.model_validate(override).model_dump(mode="json")
        await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
        await self.cache_invalidate()
        return override

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        override = await self._fetch_override(id)
        before = MembershipPermissionOverrideResponse.model_validate(override).model_dump(mode="json")
        await self._uow.membership_permission_overrides.delete(override)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

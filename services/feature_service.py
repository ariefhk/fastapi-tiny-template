import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.feature_model import FeatureKindEnum, FeatureModel
from schemas.requests.feature_request import (
    FeatureCreateRequest,
    FeatureFilterRequest,
    FeatureUpdateRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.feature_response import FeatureResponse
from services.activity_log_service import ActivityLogMixin


class FeatureService(ActivityLogMixin):
    _TABLE = FeatureModel.__tablename__
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
    def cache_get_by_id_key(feature_id: UUID) -> str:
        return f"{FeatureService._CACHE_PREFIX}:id={feature_id}"

    @staticmethod
    def cache_get_by_key_key(key: str) -> str:
        return f"{FeatureService._CACHE_PREFIX}:key={key}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        key: str | None,
        name: str | None,
        kind: FeatureKindEnum | None,
    ) -> str:
        return (
            f"{FeatureService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":key={key}:name={name}:kind={kind}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all feature cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{FeatureService._CACHE_PREFIX}:*")

    async def _fetch_feature(self, id: UUID) -> FeatureModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        feature = await self._uow.features.get_by_id(id)
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return feature

    async def get_by_id(self, id: UUID) -> FeatureModel:
        """Return a single feature or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return FeatureResponse.model_validate_json(cached)  # type: ignore[return-value]

        feature = await self._fetch_feature(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                FeatureResponse.model_validate(feature).model_dump_json(),
            )
        return feature

    async def get_by_key(self, key: str) -> FeatureModel:
        """Return a single feature by unique key or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_key_key(key))
            if cached is not None:
                return FeatureResponse.model_validate_json(cached)  # type: ignore[return-value]

        feature = await self._uow.features.get_by_key(key)
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_key_key(key),
                FeatureResponse.model_validate(feature).model_dump_json(),
            )
        return feature

    async def get_all(
        self,
        filters: FeatureFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[FeatureModel], int]:
        """Return a paginated list of features and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            key=filters.key,
            name=filters.name,
            kind=filters.kind,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [FeatureResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.features.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [FeatureResponse.model_validate(f).model_dump(mode="json") for f in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: FeatureCreateRequest) -> FeatureModel:
        """Create a feature, log the action, and return it with all fields resolved."""
        feature = await self._uow.features.create(
            key=body.key,
            name=body.name,
            kind=body.kind,
        )
        await self._uow.flush()
        await self._uow.refresh(feature)
        after = FeatureResponse.model_validate(feature).model_dump(mode="json")
        await self._log_activity(feature.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return feature

    async def update(self, id: UUID, body: FeatureUpdateRequest) -> FeatureModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated feature."""
        feature = await self._fetch_feature(id)
        before = FeatureResponse.model_validate(feature).model_dump(mode="json")
        update_data = body.model_dump(exclude_none=True)
        await self._uow.features.update(feature, **update_data)
        await self._uow.flush()
        await self._uow.refresh(feature)
        after = FeatureResponse.model_validate(feature).model_dump(mode="json")
        await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
        await self.cache_invalidate()
        return feature

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        feature = await self._fetch_feature(id)
        before = FeatureResponse.model_validate(feature).model_dump(mode="json")
        await self._uow.features.delete(feature)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.company_model import CompanyModel
from schemas.requests.company_request import (
    CompanyCreateRequest,
    CompanyFilterRequest,
    CompanyUpdateRequest,
)
# Imported for Redis serialization and activity-log snapshots — not for response shaping.
from schemas.responses.company_response import CompanyResponse
from services.activity_log_service import ActivityLogMixin


class CompanyService(ActivityLogMixin):
    _TABLE = CompanyModel.__tablename__
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
    def cache_get_by_id_key(company_id: UUID) -> str:
        return f"{CompanyService._CACHE_PREFIX}:id={company_id}"

    @staticmethod
    def cache_get_by_slug_key(slug: str) -> str:
        return f"{CompanyService._CACHE_PREFIX}:slug={slug}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        name: str | None,
        slug: str | None,
        owner_user_id: UUID | None,
    ) -> str:
        return (
            f"{CompanyService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":name={name}:slug={slug}:owner={owner_user_id}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all company cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{CompanyService._CACHE_PREFIX}:*")

    async def _fetch_company(self, id: UUID) -> CompanyModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        company = await self._uow.companies.get_by_id(id)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return company

    async def get_by_id(self, id: UUID) -> CompanyModel:
        """Return a single company or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return CompanyResponse.model_validate_json(cached)  # type: ignore[return-value]

        company = await self._fetch_company(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                CompanyResponse.model_validate(company).model_dump_json(),
            )
        return company

    async def get_by_slug(self, slug: str) -> CompanyModel:
        """Return a single company by slug or raise 404. Result cached."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_slug_key(slug))
            if cached is not None:
                return CompanyResponse.model_validate_json(cached)  # type: ignore[return-value]

        company = await self._uow.companies.get_by_slug(slug)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_slug_key(slug),
                CompanyResponse.model_validate(company).model_dump_json(),
            )
        return company

    async def get_all(
        self,
        filters: CompanyFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[CompanyModel], int]:
        """Return a paginated list of companies and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            name=filters.name,
            slug=filters.slug,
            owner_user_id=filters.owner_user_id,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [CompanyResponse.model_validate(i) for i in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.companies.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps({
                "items": [CompanyResponse.model_validate(c).model_dump(mode="json") for c in items],
                "total": total,
            })
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: CompanyCreateRequest) -> CompanyModel:
        """Create a company, log the action, and return it with all fields resolved."""
        company = await self._uow.companies.create(
            name=body.name,
            slug=body.slug,
            owner_user_id=body.owner_user_id,
        )
        await self._uow.flush()
        await self._uow.refresh(company)
        after = CompanyResponse.model_validate(company).model_dump(mode="json")
        await self._log_activity(company.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return company

    async def update(self, id: UUID, body: CompanyUpdateRequest) -> CompanyModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated company."""
        company = await self._fetch_company(id)
        before = CompanyResponse.model_validate(company).model_dump(mode="json")
        update_data = body.model_dump(exclude_none=True)
        await self._uow.companies.update(company, **update_data)
        await self._uow.flush()
        await self._uow.refresh(company)
        after = CompanyResponse.model_validate(company).model_dump(mode="json")
        await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
        await self.cache_invalidate()
        return company

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        company = await self._fetch_company(id)
        before = CompanyResponse.model_validate(company).model_dump(mode="json")
        await self._uow.companies.delete(company)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

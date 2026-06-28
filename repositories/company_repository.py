import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.company_model import CompanyModel
from schemas.requests.company_request import CompanyFilterRequest


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for companies."""
        return select(CompanyModel)

    def _apply_filters(self, stmt, filters: CompanyFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.name is not None:
            conditions.append(CompanyModel.name.ilike(f"%{filters.name}%"))
        if filters.slug is not None:
            conditions.append(CompanyModel.slug.ilike(f"%{filters.slug}%"))
        if filters.owner_user_id is not None:
            conditions.append(CompanyModel.owner_user_id == filters.owner_user_id)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> CompanyModel | None:
        """Return a single company by primary key, or None if not found."""
        stmt = self._base_query().where(CompanyModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> CompanyModel | None:
        """Return a single company by slug, or None if not found."""
        stmt = self._base_query().where(CompanyModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: CompanyFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[CompanyModel], int]:
        """Return a page of companies matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(CompanyModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(CompanyModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        name: str,
        slug: str,
        owner_user_id: uuid.UUID | None = None,
    ) -> CompanyModel:
        """Stage a new company. Persisted on the next flush/commit."""
        company = CompanyModel(name=name, slug=slug, owner_user_id=owner_user_id)
        self._session.add(company)
        return company

    async def update(self, company: CompanyModel, **kwargs) -> CompanyModel:
        """Apply *kwargs* fields to *company* in place and return it."""
        for key, value in kwargs.items():
            setattr(company, key, value)
        return company

    async def delete(self, company: CompanyModel) -> None:
        """Hard-delete a single company."""
        await self._session.delete(company)

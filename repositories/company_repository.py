import uuid

from sqlalchemy import select
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

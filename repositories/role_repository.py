import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.role_model import RoleModel
from schemas.requests.role_request import RoleFilterRequest


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for roles."""
        return select(RoleModel)

    def _apply_filters(self, stmt, filters: RoleFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.company_id is not None:
            conditions.append(RoleModel.company_id == filters.company_id)
        if filters.name is not None:
            conditions.append(RoleModel.name.ilike(f"%{filters.name}%"))
        if filters.slug is not None:
            conditions.append(RoleModel.slug.ilike(f"%{filters.slug}%"))
        if filters.is_system is not None:
            conditions.append(RoleModel.is_system == filters.is_system)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> RoleModel | None:
        """Return a single role by primary key, or None if not found."""
        stmt = self._base_query().where(RoleModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: RoleFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[RoleModel], int]:
        """Return a page of roles matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(RoleModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(RoleModel.created_at.desc())
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
        company_id: uuid.UUID | None = None,
        is_system: bool = False,
    ) -> RoleModel:
        """Stage a new role. Persisted on the next flush/commit."""
        role = RoleModel(name=name, slug=slug, company_id=company_id, is_system=is_system)
        self._session.add(role)
        return role

    async def update(self, role: RoleModel, **kwargs) -> RoleModel:
        """Apply *kwargs* fields to *role* in place and return it."""
        for key, value in kwargs.items():
            setattr(role, key, value)
        return role

    async def delete(self, role: RoleModel) -> None:
        """Hard-delete a single role."""
        await self._session.delete(role)

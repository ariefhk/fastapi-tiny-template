import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.membership_role_model import MembershipRoleModel
from schemas.requests.membership_role_request import MembershipRoleFilterRequest


class MembershipRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for membership roles."""
        return select(MembershipRoleModel)

    def _apply_filters(self, stmt, filters: MembershipRoleFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.membership_id is not None:
            conditions.append(MembershipRoleModel.membership_id == filters.membership_id)
        if filters.role_id is not None:
            conditions.append(MembershipRoleModel.role_id == filters.role_id)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> MembershipRoleModel | None:
        """Return a single membership role by primary key, or None if not found."""
        stmt = self._base_query().where(MembershipRoleModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: MembershipRoleFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipRoleModel], int]:
        """Return a page of membership roles matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(MembershipRoleModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(MembershipRoleModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> MembershipRoleModel:
        """Stage a new membership role link. Persisted on the next flush/commit."""
        membership_role = MembershipRoleModel(membership_id=membership_id, role_id=role_id)
        self._session.add(membership_role)
        return membership_role

    async def delete(self, membership_role: MembershipRoleModel) -> None:
        """Hard-delete a single membership role link."""
        await self._session.delete(membership_role)

import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.membership_model import MembershipModel, MembershipStatusEnum
from schemas.requests.membership_request import MembershipFilterRequest


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for memberships."""
        return select(MembershipModel)

    def _apply_filters(self, stmt, filters: MembershipFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.user_id is not None:
            conditions.append(MembershipModel.user_id == filters.user_id)
        if filters.company_id is not None:
            conditions.append(MembershipModel.company_id == filters.company_id)
        if filters.status is not None:
            conditions.append(MembershipModel.status == filters.status)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> MembershipModel | None:
        """Return a single membership by primary key, or None if not found."""
        stmt = self._base_query().where(MembershipModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_company(
        self, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> MembershipModel | None:
        """Return the membership for a specific user-company pair, or None if not found."""
        stmt = self._base_query().where(
            MembershipModel.user_id == user_id,
            MembershipModel.company_id == company_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: MembershipFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipModel], int]:
        """Return a page of memberships matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(MembershipModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(MembershipModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        status: MembershipStatusEnum = MembershipStatusEnum.ACTIVE,
    ) -> MembershipModel:
        """Stage a new membership. Persisted on the next flush/commit."""
        membership = MembershipModel(user_id=user_id, company_id=company_id, status=status)
        self._session.add(membership)
        return membership

    async def update(self, membership: MembershipModel, **kwargs) -> MembershipModel:
        """Apply *kwargs* fields to *membership* in place and return it."""
        for key, value in kwargs.items():
            setattr(membership, key, value)
        return membership

    async def delete(self, membership: MembershipModel) -> None:
        """Hard-delete a single membership."""
        await self._session.delete(membership)

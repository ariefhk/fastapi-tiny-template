import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.membership_permission_override_model import (
    MembershipPermissionOverrideModel,
    OverrideEffectEnum,
)
from schemas.requests.membership_permission_override_request import (
    MembershipPermissionOverrideFilterRequest,
)


class MembershipPermissionOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for membership permission overrides."""
        return select(MembershipPermissionOverrideModel)

    def _apply_filters(self, stmt, filters: MembershipPermissionOverrideFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.membership_id is not None:
            conditions.append(
                MembershipPermissionOverrideModel.membership_id == filters.membership_id
            )
        if filters.permission_id is not None:
            conditions.append(
                MembershipPermissionOverrideModel.permission_id == filters.permission_id
            )
        if filters.effect is not None:
            conditions.append(MembershipPermissionOverrideModel.effect == filters.effect)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> MembershipPermissionOverrideModel | None:
        """Return a single override by primary key, or None if not found."""
        stmt = self._base_query().where(MembershipPermissionOverrideModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_membership_and_permission(
        self, membership_id: uuid.UUID, permission_id: uuid.UUID
    ) -> MembershipPermissionOverrideModel | None:
        """Return the override for a membership-permission pair, or None if not found."""
        stmt = self._base_query().where(
            MembershipPermissionOverrideModel.membership_id == membership_id,
            MembershipPermissionOverrideModel.permission_id == permission_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: MembershipPermissionOverrideFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[MembershipPermissionOverrideModel], int]:
        """Return a page of overrides matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(MembershipPermissionOverrideModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(MembershipPermissionOverrideModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        membership_id: uuid.UUID,
        permission_id: uuid.UUID,
        effect: OverrideEffectEnum,
    ) -> MembershipPermissionOverrideModel:
        """Stage a new permission override. Persisted on the next flush/commit."""
        override = MembershipPermissionOverrideModel(
            membership_id=membership_id,
            permission_id=permission_id,
            effect=effect,
        )
        self._session.add(override)
        return override

    async def update(
        self, override: MembershipPermissionOverrideModel, **kwargs
    ) -> MembershipPermissionOverrideModel:
        """Apply *kwargs* fields to *override* in place and return it."""
        for key, value in kwargs.items():
            setattr(override, key, value)
        return override

    async def delete(self, override: MembershipPermissionOverrideModel) -> None:
        """Hard-delete a single permission override."""
        await self._session.delete(override)

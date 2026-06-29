import uuid

from sqlalchemy import delete as db_delete
from sqlalchemy import select
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
            conditions.append(
                MembershipRoleModel.membership_id == filters.membership_id
            )
        if filters.role_id is not None:
            conditions.append(MembershipRoleModel.role_id == filters.role_id)
        return stmt.where(*conditions)

    async def create(
        self,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> MembershipRoleModel:
        """Stage a new membership role link. Persisted on the next flush/commit."""
        membership_role = MembershipRoleModel(
            membership_id=membership_id, role_id=role_id
        )
        self._session.add(membership_role)
        return membership_role

    async def delete_by_membership(self, membership_id: uuid.UUID) -> None:
        stmt = db_delete(MembershipRoleModel).where(
            MembershipRoleModel.membership_id == membership_id
        )
        await self._session.execute(stmt)

import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.role_permission_model import RolePermissionModel
from schemas.requests.role_permission_request import RolePermissionFilterRequest


class RolePermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for role permissions."""
        return select(RolePermissionModel)

    def _apply_filters(self, stmt, filters: RolePermissionFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.role_id is not None:
            conditions.append(RolePermissionModel.role_id == filters.role_id)
        if filters.permission_id is not None:
            conditions.append(RolePermissionModel.permission_id == filters.permission_id)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> RolePermissionModel | None:
        """Return a single role permission by primary key, or None if not found."""
        stmt = self._base_query().where(RolePermissionModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: RolePermissionFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[RolePermissionModel], int]:
        """Return a page of role permissions matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(RolePermissionModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(RolePermissionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> RolePermissionModel:
        """Stage a new role permission link. Persisted on the next flush/commit."""
        role_permission = RolePermissionModel(role_id=role_id, permission_id=permission_id)
        self._session.add(role_permission)
        return role_permission

    async def delete(self, role_permission: RolePermissionModel) -> None:
        """Hard-delete a single role permission link."""
        await self._session.delete(role_permission)

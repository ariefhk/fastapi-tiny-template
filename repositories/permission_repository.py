import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.permission_model import PermissionModel
from schemas.requests.permission_request import PermissionFilterRequest


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(PermissionModel)

    def _apply_filters(self, stmt, filters: PermissionFilterRequest):
        conditions = []
        if filters.key is not None:
            conditions.append(PermissionModel.key.ilike(f"%{filters.key}%"))
        if filters.resource is not None:
            conditions.append(PermissionModel.resource.ilike(f"%{filters.resource}%"))
        if filters.action is not None:
            conditions.append(PermissionModel.action.ilike(f"%{filters.action}%"))
        return stmt.where(*conditions)

    async def get_by_id(self, permission_id: uuid.UUID) -> Optional[PermissionModel]:
        result = await self._session.execute(
            self._base_query().where(PermissionModel.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[PermissionModel]:
        result = await self._session.execute(
            self._base_query().where(PermissionModel.key == key)
        )
        return result.scalar_one_or_none()

    async def get_all_ids(self) -> List[uuid.UUID]:
        result = await self._session.execute(select(PermissionModel.id))
        ids: List[uuid.UUID] = []
        for row in result.all():
            ids.append(row[0])
        return ids

    async def get_all(
        self,
        filters: PermissionFilterRequest,
        offset: int,
        limit: int,
    ) -> Tuple[List[PermissionModel], int]:
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(PermissionModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        result = await self._session.execute(
            filter_stmt.order_by(PermissionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(
        self,
        key: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
    ) -> PermissionModel:
        permission = PermissionModel(
            key=key,
            resource=resource,
            action=action,
            description=description,
        )
        self._session.add(permission)
        return permission

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.permission_model import PermissionModel


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

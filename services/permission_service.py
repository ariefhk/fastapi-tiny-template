import uuid
from typing import List, Tuple

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from schemas.requests.permission_request import PermissionFilterRequest
from schemas.responses.permission_response import PermissionResponse


class PermissionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get_all(self, page: int = 1, limit: int = 50) -> Tuple[List[PermissionResponse], int]:
        offset = (page - 1) * limit
        result = await self._uow.permissions.get_all(PermissionFilterRequest(), offset, limit)
        permissions = result[0]
        total = result[1]

        response_list: List[PermissionResponse] = []
        for permission in permissions:
            response_list.append(PermissionResponse.model_validate(permission))

        return response_list, total

    async def get_one(self, permission_id: uuid.UUID) -> PermissionResponse:
        permission = await self._uow.permissions.get_by_id(permission_id)
        if permission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return PermissionResponse.model_validate(permission)

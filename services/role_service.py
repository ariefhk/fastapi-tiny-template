import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from models.activity_log_model import ActivityLogAction
from models.role_model import RoleModel
from schemas.requests.role_request import RoleCreateRequest, RoleFilterRequest, RoleUpdateRequest
from schemas.responses.role_response import RoleResponse
from services.activity_log_service import ActivityLogMixin


class RoleService(ActivityLogMixin):
    _TABLE = RoleModel.__tablename__

    def __init__(
        self,
        uow: UnitOfWork,
        company_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self._uow = uow
        self._company_id = company_id
        self._actor_id = actor_id
        self._ip_address = ip_address
        self._user_agent = user_agent

    async def get_all(self, page: int = 1, limit: int = 10) -> Tuple[List[RoleResponse], int]:
        roles, total = await self._uow.roles.get_all(
            RoleFilterRequest(company_id=self._company_id), page=page, limit=limit
        )
        return [RoleResponse.model_validate(r) for r in roles], total

    async def get_one(self, role_id: uuid.UUID) -> RoleResponse:
        role = await self._uow.roles.get_by_id(role_id)
        if role is None or role.company_id != self._company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return RoleResponse.model_validate(role)

    async def create(self, payload: RoleCreateRequest) -> RoleResponse:
        existing = await self._uow.roles.get_by_slug(payload.slug, self._company_id)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role slug already exists")

        role = await self._uow.roles.create(
            company_id=self._company_id,
            name=payload.name,
            slug=payload.slug,
            is_system=False,
        )
        await self._log_activity(table_id=role.id, action=ActivityLogAction.CREATE)
        await self._uow.commit()
        await self._uow.refresh(role)
        return RoleResponse.model_validate(role)

    async def update(self, role_id: uuid.UUID, payload: RoleUpdateRequest) -> RoleResponse:
        role = await self._uow.roles.get_by_id(role_id)
        if role is None or role.company_id != self._company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.is_system is True:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System roles cannot be modified")

        fields = payload.model_dump(mode="json", exclude_unset=True)
        await self._uow.roles.update(role, **fields)
        await self._log_activity(table_id=role_id, action=ActivityLogAction.UPDATE)
        await self._uow.commit()
        await self._uow.refresh(role)
        return RoleResponse.model_validate(role)

    async def delete(self, role_id: uuid.UUID) -> None:
        role = await self._uow.roles.get_by_id(role_id)
        if role is None or role.company_id != self._company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.is_system is True:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System roles cannot be deleted")

        await self._uow.roles.delete(role)
        await self._log_activity(table_id=role_id, action=ActivityLogAction.DELETE)
        await self._uow.commit()

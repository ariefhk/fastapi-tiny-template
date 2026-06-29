import uuid
from typing import List, Tuple

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from models.activity_log_model import ActivityLogAction
from models.membership_model import MembershipModel
from schemas.requests.member_request import MemberOverrideCreate, MemberRoleAssignment
from schemas.requests.membership_request import MembershipFilterRequest
from schemas.responses.member_response import MemberResponse
from services.activity_log_service import ActivityLogMixin


class MemberService(ActivityLogMixin):
    _TABLE = MembershipModel.__tablename__

    def __init__(
        self,
        uow: UnitOfWork,
        company_id: uuid.UUID,
        actor_id=None,
        ip_address=None,
        user_agent=None,
    ) -> None:
        self._uow = uow
        self._company_id = company_id
        self._actor_id = actor_id
        self._ip_address = ip_address
        self._user_agent = user_agent

    async def get_all(
        self, page: int = 1, limit: int = 10
    ) -> Tuple[List[MemberResponse], int]:
        filters = MembershipFilterRequest(company_id=self._company_id)
        memberships, total = await self._uow.memberships.get_all(filters, page=page, limit=limit)

        response_list: List[MemberResponse] = []
        for membership in memberships:
            role_ids = await self._uow.memberships.get_list_role_ids_by_membership(membership.id)
            user = await self._uow.users.get_by_id(membership.user_id)
            response_list.append(
                MemberResponse(
                    membership_id=membership.id,
                    user_id=membership.user_id,
                    email=user.email if user is not None else "",
                    name=user.name if user is not None else None,
                    status=membership.status,
                    role_ids=role_ids,
                    joined_at=membership.created_at,
                )
            )

        return response_list, total

    async def assign_roles(
        self, membership_id: uuid.UUID, payload: MemberRoleAssignment
    ) -> MemberResponse:
        membership = await self._uow.memberships.get_by_id(
            membership_id, self._company_id
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )

        for role_id in payload.role_ids:
            role = await self._uow.roles.get_by_id(role_id)
            if role is None or role.company_id != self._company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role does not belong to company",
                )

        await self._uow.membership_roles.delete_by_membership(membership_id)
        for role_id in payload.role_ids:
            await self._uow.membership_roles.create(membership_id, role_id)

        await self._log_activity(table_id=membership_id, action=ActivityLogAction.UPDATE)
        await self._uow.commit()

        role_ids = await self._uow.memberships.get_list_role_ids_by_membership(membership_id)
        user = await self._uow.users.get_by_id(membership.user_id)
        return MemberResponse(
            membership_id=membership.id,
            user_id=membership.user_id,
            email=user.email if user is not None else "",
            name=user.name if user is not None else None,
            status=membership.status,
            role_ids=role_ids,
            joined_at=membership.created_at,
        )

    async def add_override(
        self, membership_id: uuid.UUID, payload: MemberOverrideCreate
    ) -> None:
        membership = await self._uow.memberships.get_by_id(
            membership_id, self._company_id
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )

        permission = await self._uow.permissions.get_by_key(payload.permission_key)
        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown permission"
            )

        existing = await self._uow.membership_permission_overrides.get_by_membership_and_permission(
            membership_id, permission.id
        )
        if existing is None:
            await self._uow.membership_permission_overrides.create(
                membership_id, permission.id, payload.effect
            )
        else:
            await self._uow.membership_permission_overrides.update(existing, effect=payload.effect)

        await self._log_activity(table_id=membership_id, action=ActivityLogAction.UPDATE)
        await self._uow.commit()

    async def remove(self, membership_id: uuid.UUID) -> None:
        membership = await self._uow.memberships.get_by_id(
            membership_id, self._company_id
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )

        await self._uow.memberships.delete(membership)
        await self._log_activity(table_id=membership_id, action=ActivityLogAction.DELETE)
        await self._uow.commit()

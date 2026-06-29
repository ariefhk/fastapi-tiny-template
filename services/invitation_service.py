import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from fastapi import HTTPException, status

from commons.security import hash_password
from databases.unit_of_work import UnitOfWork
from models.activity_log_model import ActivityLogAction
from models.auth_identity_model import AuthProviderEnum
from models.invitation_model import InvitationModel, InvitationStatusEnum
from models.membership_model import MembershipStatusEnum
from schemas.requests.invitation_request import InvitationAccept, InvitationCreate
from schemas.responses.invitation_response import InvitationResponse
from services.activity_log_service import ActivityLogMixin


class InvitationService(ActivityLogMixin):
    _TABLE = InvitationModel.__tablename__

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
    ) -> Tuple[List[InvitationResponse], int]:
        offset = (page - 1) * limit
        result = await self._uow.invitations.get_all(self._company_id, offset, limit)
        invitations = result[0]
        total = result[1]

        response_list: List[InvitationResponse] = []
        for invitation in invitations:
            response_list.append(InvitationResponse.model_validate(invitation))

        return response_list, total

    async def create(self, payload: InvitationCreate) -> InvitationResponse:
        if payload.role_id is not None:
            role = await self._uow.roles.get_by_id(payload.role_id)
            if role is None or role.company_id != self._company_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role does not belong to company",
                )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = await self._uow.invitations.create(
            company_id=self._company_id,
            email=payload.email,
            role_id=payload.role_id,
            token=token,
            invited_by_user_id=self._actor_id,
            expires_at=expires_at,
        )
        await self._log_activity(
            table_id=invitation.id, action=ActivityLogAction.CREATE
        )
        await self._uow.commit()
        await self._uow.refresh(invitation)
        return InvitationResponse.model_validate(invitation)

    async def revoke(self, invitation_id: uuid.UUID) -> None:
        invitation = await self._uow.invitations.get_by_id(
            invitation_id, self._company_id
        )
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
            )

        invitation.status = InvitationStatusEnum.REVOKED
        await self._log_activity(
            table_id=invitation_id, action=ActivityLogAction.UPDATE
        )
        await self._uow.commit()

    async def accept(self, payload: InvitationAccept) -> InvitationResponse:
        invitation = await self._uow.invitations.get_by_token(payload.token)
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
            )
        if invitation.status != InvitationStatusEnum.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Invitation not pending"
            )
        if invitation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Invitation expired"
            )

        user = await self._uow.users.get_by_email(invitation.email)
        if user is None:
            now = datetime.now(timezone.utc)
            user = await self._uow.users.create(
                email=invitation.email, name=payload.name, email_verified_at=now
            )
            await self._uow.auth_identities.create(
                user_id=user.id,
                provider=AuthProviderEnum.PASSWORD.value,
                provider_user_id=None,
                password_hash=hash_password(payload.password),
                email=invitation.email,
            )

        membership = await self._uow.memberships.get_by_user_and_company(
            user.id, invitation.company_id
        )
        if membership is None:
            membership = await self._uow.memberships.create(
                user_id=user.id,
                company_id=invitation.company_id,
                status=MembershipStatusEnum.ACTIVE,
            )

        if invitation.role_id is not None:
            await self._uow.membership_roles.create(membership.id, invitation.role_id)

        invitation.status = InvitationStatusEnum.ACCEPTED
        await self._uow.commit()
        await self._uow.refresh(invitation)
        return InvitationResponse.model_validate(invitation)

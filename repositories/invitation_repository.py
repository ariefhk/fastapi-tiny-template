import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.invitation_model import InvitationModel, InvitationStatusEnum


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        company_id: uuid.UUID,
        email: str,
        token: str,
        expires_at: datetime,
        role_id: Optional[uuid.UUID] = None,
        invited_by_user_id: Optional[uuid.UUID] = None,
        status: InvitationStatusEnum = InvitationStatusEnum.PENDING,
    ) -> InvitationModel:
        invitation = InvitationModel(
            company_id=company_id,
            email=email,
            token=token,
            expires_at=expires_at,
            role_id=role_id,
            invited_by_user_id=invited_by_user_id,
            status=status,
        )
        self._session.add(invitation)
        return invitation

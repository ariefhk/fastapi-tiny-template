import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.invitation_model import InvitationModel, InvitationStatusEnum


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(InvitationModel)

    async def get_all(
        self, company_id: uuid.UUID, offset: int, limit: int
    ) -> Tuple[List[InvitationModel], int]:
        base = self._base_query().where(InvitationModel.company_id == company_id)
        total = (
            await self._session.execute(
                select(func.count()).select_from(InvitationModel).where(
                    InvitationModel.company_id == company_id
                )
            )
        ).scalar_one()
        result = await self._session.execute(
            base.order_by(InvitationModel.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_by_id(
        self, invitation_id: uuid.UUID, company_id: uuid.UUID
    ) -> InvitationModel | None:
        stmt = self._base_query().where(
            InvitationModel.id == invitation_id,
            InvitationModel.company_id == company_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> InvitationModel | None:
        stmt = self._base_query().where(InvitationModel.token == token)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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

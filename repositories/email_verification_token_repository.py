import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.email_verification_model import EmailVerificationTokenModel


class EmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(
        self, token_hash: str
    ) -> EmailVerificationTokenModel | None:
        """Return a single token by its SHA-256 hash, or None if not found."""
        stmt = select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        verified_at: Optional[datetime] = None,
    ) -> EmailVerificationTokenModel:
        """Stage a new email verification token. Persisted on the next flush/commit."""
        token = EmailVerificationTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            verified_at=verified_at,
        )
        self._session.add(token)
        return token

    async def update(
        self, token: EmailVerificationTokenModel, **kwargs
    ) -> EmailVerificationTokenModel:
        """Apply *kwargs* fields to *token* in place and return it."""
        for key, value in kwargs.items():
            setattr(token, key, value)
        return token

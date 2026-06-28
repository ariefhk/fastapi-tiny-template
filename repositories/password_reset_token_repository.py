import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset_token_model import PasswordResetTokenModel


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetTokenModel | None:
        """Return a single token by its SHA-256 hash, or None if not found."""
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        used_at: Optional[datetime] = None,
    ) -> PasswordResetTokenModel:
        """Stage a new password reset token. Persisted on the next flush/commit."""
        token = PasswordResetTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=used_at,
        )
        self._session.add(token)
        return token

    async def update(
        self, token: PasswordResetTokenModel, **kwargs
    ) -> PasswordResetTokenModel:
        """Apply *kwargs* fields to *token* in place and return it."""
        for key, value in kwargs.items():
            setattr(token, key, value)
        return token

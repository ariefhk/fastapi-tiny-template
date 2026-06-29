import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_identity_model import AuthIdentityModel, AuthProviderEnum


class AuthIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_password_identity(
        self, user_id: uuid.UUID
    ) -> Optional[AuthIdentityModel]:
        """Return the password identity for a user, or None if not found."""
        stmt = (
            select(AuthIdentityModel)
            .where(AuthIdentityModel.user_id == user_id)
            .where(AuthIdentityModel.provider == AuthProviderEnum.PASSWORD.value)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider(
        self, provider: str, provider_user_id: str
    ) -> Optional[AuthIdentityModel]:
        """Return the identity matching a provider and its user ID, or None if not found."""
        stmt = (
            select(AuthIdentityModel)
            .where(AuthIdentityModel.provider == provider)
            .where(AuthIdentityModel.provider_user_id == provider_user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: Optional[str],
        password_hash: Optional[str],
        email: Optional[str],
    ) -> AuthIdentityModel:
        """Stage a new auth identity. Persisted on the next flush/commit."""
        item = AuthIdentityModel(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            password_hash=password_hash,
            email=email,
        )
        self._session.add(item)
        return item

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_identity_model import AuthIdentityModel, AuthProviderEnum


class AuthIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_and_provider(
        self, user_id: uuid.UUID, provider: AuthProviderEnum
    ) -> AuthIdentityModel | None:
        """Return the identity for a user + provider pair, or None if not found."""
        stmt = select(AuthIdentityModel).where(
            AuthIdentityModel.user_id == user_id,
            AuthIdentityModel.provider == provider,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_and_provider(
        self, email: str, provider: AuthProviderEnum
    ) -> AuthIdentityModel | None:
        """Return the identity for an email + provider pair, or None if not found."""
        stmt = select(AuthIdentityModel).where(
            AuthIdentityModel.email == email,
            AuthIdentityModel.provider == provider,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        provider: AuthProviderEnum,
        provider_user_id: Optional[str] = None,
        password_hash: Optional[str] = None,
        email: Optional[str] = None,
    ) -> AuthIdentityModel:
        """Stage a new auth identity. Persisted on the next flush/commit."""
        identity = AuthIdentityModel(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            password_hash=password_hash,
            email=email,
        )
        self._session.add(identity)
        return identity

    async def update(self, identity: AuthIdentityModel, **kwargs) -> AuthIdentityModel:
        """Apply *kwargs* fields to *identity* in place and return it."""
        for key, value in kwargs.items():
            setattr(identity, key, value)
        return identity

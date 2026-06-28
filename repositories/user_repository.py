import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_model import UserModel
from schemas.requests.user_request import UserFilterRequest


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT with last_active_company eagerly loaded."""
        return select(UserModel)

    def _apply_filters(self, stmt, filters: UserFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []

        if filters.email is not None:
            conditions.append(UserModel.email.ilike(f"%{filters.email}%"))
        if filters.name is not None:
            conditions.append(UserModel.name.ilike(f"%{filters.name}%"))
        if filters.mfa_enabled is not None:
            conditions.append(UserModel.mfa_enabled == filters.mfa_enabled)
        if filters.email_verified is not None:
            if filters.email_verified:
                conditions.append(UserModel.email_verified_at.is_not(None))
            else:
                conditions.append(UserModel.email_verified_at.is_(None))
        if filters.last_active_company_id is not None:
            conditions.append(
                UserModel.last_active_company_id == filters.last_active_company_id
            )

        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> UserModel | None:
        """Return a single user by primary key, or None if not found."""
        stmt = self._base_query().where(UserModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """Return a single user by email, or None if not found."""
        stmt = self._base_query().where(UserModel.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: UserFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[UserModel], int]:
        """Return a page of users matching *filters* and the total count.

        The total count is fetched in the same call so callers can build
        pagination metadata without a separate round-trip.
        """
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)

        count_stmt = self._apply_filters(
            select(func.count()).select_from(UserModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            filter_stmt.order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        email: str,
        name: Optional[str] = None,
        mfa_enabled: bool = False,
        email_verified_at: Optional[datetime] = None,
        last_active_company_id: Optional[uuid.UUID] = None,
    ) -> UserModel:
        """Stage a new user. Persisted on the next flush/commit."""
        user = UserModel(
            email=email,
            name=name,
            mfa_enabled=mfa_enabled,
            email_verified_at=email_verified_at,
            last_active_company_id=last_active_company_id,
        )
        self._session.add(user)
        return user

    async def update(self, user: UserModel, **kwargs) -> UserModel:
        """Apply *kwargs* fields to *user* in place and return it."""
        for key, value in kwargs.items():
            setattr(user, key, value)
        return user

    async def delete(self, user: UserModel) -> None:
        """Hard-delete a single user."""
        await self._session.delete(user)

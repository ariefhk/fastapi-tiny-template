import json
from typing import List, Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.config import get_configs
from databases.unit_of_work import UnitOfWork
from infrastructures.redis.helper import delete_cache_pattern, get_cache, set_cache
from models.activity_log_model import ActivityLogAction
from models.user_model import UserModel
from schemas.requests.user_request import (
    UserCreateRequest,
    UserFilterRequest,
    UserUpdateRequest,
)
from schemas.responses.user_response import UserResponse
from services.activity_log_service import ActivityLogMixin


class UserService(ActivityLogMixin):
    _TABLE = UserModel.__tablename__
    _CACHE_PREFIX = _TABLE

    def __init__(
        self,
        uow: UnitOfWork,
        actor_id: UUID | None = None,
        company_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._uow = uow
        self._actor_id = actor_id
        self._company_id = company_id
        self._ip_address = ip_address
        self._user_agent = user_agent

    @staticmethod
    def cache_get_by_id_key(user_id: UUID) -> str:
        return f"{UserService._CACHE_PREFIX}:id={user_id}"

    @staticmethod
    def cache_get_by_email_key(email: str) -> str:
        return f"{UserService._CACHE_PREFIX}:email={email}"

    @staticmethod
    def cache_get_all_key(
        page: int,
        limit: int,
        email: str | None,
        name: str | None,
        mfa_enabled: bool | None,
        email_verified: bool | None,
        last_active_company_id: UUID | None,
    ) -> str:
        return (
            f"{UserService._CACHE_PREFIX}:list:page={page}:limit={limit}"
            f":email={email}:name={name}:mfa_enabled={mfa_enabled}"
            f":email_verified={email_verified}:company={last_active_company_id}"
        )

    @staticmethod
    async def cache_invalidate() -> None:
        """Delete all user cache keys (items + lists)."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            await delete_cache_pattern(f"{UserService._CACHE_PREFIX}:*")

    async def _fetch_user(self, id: UUID) -> UserModel:
        """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
        user = await self._uow.users.get_by_id(id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def get_by_id(self, id: UUID) -> UserModel:
        """Return a single user or raise 404. Result cached for 5 minutes."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_id_key(id))
            if cached is not None:
                return UserResponse.model_validate_json(cached)  # type: ignore[return-value]

        user = await self._fetch_user(id)

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_id_key(id),
                UserResponse.model_validate(user).model_dump_json(),
            )
        return user

    async def get_by_email(self, email: str) -> UserModel:
        """Return a single user by email or raise 404. Result cached for 5 minutes."""
        cfg = get_configs()
        if cfg.CACHE_ENABLED:
            cached = await get_cache(self.cache_get_by_email_key(email))
            if cached is not None:
                return UserResponse.model_validate_json(cached)  # type: ignore[return-value]

        user = await self._uow.users.get_by_email(email)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if cfg.CACHE_ENABLED:
            await set_cache(
                self.cache_get_by_email_key(email),
                UserResponse.model_validate(user).model_dump_json(),
            )
        return user

    async def get_all(
        self,
        filters: UserFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[UserModel], int]:
        """Return a paginated list of users and the total count. Result cached per filter combination."""
        cfg = get_configs()
        list_key = self.cache_get_all_key(
            page=page,
            limit=limit,
            email=filters.email,
            name=filters.name,
            mfa_enabled=filters.mfa_enabled,
            email_verified=filters.email_verified,
            last_active_company_id=filters.last_active_company_id,
        )

        if cfg.CACHE_ENABLED:
            cached = await get_cache(list_key)
            if cached is not None:
                data = json.loads(cached)
                items = [UserResponse.model_validate(item) for item in data["items"]]
                return items, data["total"]  # type: ignore[return-value]

        items, total = await self._uow.users.get_all(filters, page=page, limit=limit)

        if cfg.CACHE_ENABLED:
            payload = json.dumps(
                {
                    "items": [
                        UserResponse.model_validate(u).model_dump(mode="json")
                        for u in items
                    ],
                    "total": total,
                }
            )
            await set_cache(list_key, payload)

        return items, total

    async def create(self, body: UserCreateRequest) -> UserModel:
        """Create a user, log the action, and return it with all fields resolved."""
        user = await self._uow.users.create(
            email=body.email,
            name=body.name,
            mfa_enabled=body.mfa_enabled,
        )
        await self._uow.flush()
        await self._uow.refresh(user)
        after = UserResponse.model_validate(user).model_dump(mode="json")
        await self._log_activity(user.id, ActivityLogAction.CREATE, after=after)
        await self.cache_invalidate()
        return user

    async def update(self, id: UUID, body: UserUpdateRequest) -> UserModel:
        """Fetch by id, apply non-None fields from *body*, log the change, and return updated user."""
        user = await self._fetch_user(id)
        before = UserResponse.model_validate(user).model_dump(mode="json")

        update_data = body.model_dump(exclude_none=True)
        await self._uow.users.update(user, **update_data)
        await self._uow.flush()
        await self._uow.refresh(user)
        after = UserResponse.model_validate(user).model_dump(mode="json")

        await self._log_activity(
            id, ActivityLogAction.UPDATE, before=before, after=after
        )
        await self.cache_invalidate()
        return user

    async def delete(self, id: UUID) -> None:
        """Fetch by id, log the deletion, then hard-delete. Raises 404 if not found."""
        user = await self._fetch_user(id)
        before = UserResponse.model_validate(user).model_dump(mode="json")

        await self._uow.users.delete(user)
        await self._log_activity(id, ActivityLogAction.DELETE, before=before)
        await self.cache_invalidate()

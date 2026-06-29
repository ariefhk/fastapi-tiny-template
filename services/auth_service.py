import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import HTTPException, status

from commons.access import AccessContext
from commons.config import get_configs
from commons.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from databases.unit_of_work import UnitOfWork
from models.auth_identity_model import AuthProviderEnum
from models.membership_model import MembershipStatusEnum
from models.user_model import UserModel
from schemas.requests.auth_request import LoginRequest, RegisterRequest
from schemas.responses.auth_response import (
    AccessTokenResponse,
    CompanyBrief,
    MeResponse,
    TokenResponse,
)
from schemas.responses.user_response import UserResponse

_settings = get_configs()


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def _slugify(self, value: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        if base == "":
            base = "company"
        return base + "-" + secrets.token_hex(3)

    async def _new_session_tokens(
        self, user: UserModel, company_id: uuid.UUID
    ) -> TokenResponse:
        refresh_raw = generate_refresh_token()
        refresh_hash = hash_refresh_token(refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        session = await self._uow.sessions.create(
            user_id=user.id,
            active_company_id=company_id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
        )
        access_token = create_access_token(user.id, session.id, company_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_raw,
            user=UserResponse.model_validate(user),
        )

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        existing = await self._uow.users.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        user = await self._uow.users.create(
            email=payload.email, name=payload.name, email_verified_at=None
        )
        await self._uow.auth_identities.create(
            user_id=user.id,
            provider=AuthProviderEnum.PASSWORD.value,
            provider_user_id=None,
            password_hash=hash_password(payload.password),
            email=payload.email,
        )

        company = await self._uow.companies.create(
            name=payload.company_name,
            slug=self._slugify(payload.company_name),
            owner_user_id=user.id,
        )
        membership = await self._uow.memberships.create(
            user_id=user.id,
            company_id=company.id,
            status=MembershipStatusEnum.ACTIVE,
        )

        owner_role = await self._uow.roles.create(
            company_id=company.id, name="Owner", slug="owner", is_system=True
        )
        permission_ids = await self._uow.permissions.get_all_ids()
        for permission_id in permission_ids:
            await self._uow.role_permissions.create(owner_role.id, permission_id)
        await self._uow.membership_roles.create(membership.id, owner_role.id)

        await self._uow.users.update(user, last_active_company_id=company.id)

        tokens = await self._new_session_tokens(user, company.id)
        await self._uow.commit()
        return tokens

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self._uow.users.get_by_email(payload.email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        identity = await self._uow.auth_identities.get_password_identity(user.id)
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if identity.password_hash is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if verify_password(payload.password, identity.password_hash) is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        company_id = user.last_active_company_id
        if company_id is None:
            companies = await self._uow.memberships.get_list_companies_by_user(user.id)
            if len(companies) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No company membership",
                )
            company_id = companies[0].id

        tokens = await self._new_session_tokens(user, company_id)
        await self._uow.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> AccessTokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self._uow.sessions.get_by_refresh_token_hash(token_hash)
        if session_row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        if session_row.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )

        access_token = create_access_token(
            session_row.user_id, session_row.id, session_row.active_company_id
        )
        return AccessTokenResponse(access_token=access_token)

    async def switch_company(
        self, refresh_token: str, company_id: uuid.UUID
    ) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self._uow.sessions.get_by_refresh_token_hash(token_hash)
        if session_row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        membership = await self._uow.memberships.get_by_user_and_company(
            session_row.user_id, company_id
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No membership in target company",
            )

        await self._uow.sessions.set_active_company(session_row, company_id)

        new_refresh_raw = generate_refresh_token()
        new_refresh_hash = hash_refresh_token(new_refresh_raw)
        new_expires_at = datetime.now(timezone.utc) + timedelta(
            days=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._uow.sessions.rotate(session_row, new_refresh_hash, new_expires_at)

        user = await self._uow.users.get_by_id(session_row.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        await self._uow.users.update(user, last_active_company_id=company_id)

        access_token = create_access_token(session_row.user_id, session_row.id, company_id)
        await self._uow.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_raw,
            user=UserResponse.model_validate(user),
        )

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self._uow.sessions.get_by_refresh_token_hash(token_hash)
        if session_row is None:
            return
        await self._uow.sessions.delete(session_row)
        await self._uow.commit()

    async def get_me(self, context: AccessContext) -> MeResponse:
        user = await self._uow.users.get_by_id(context.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        companies = await self._uow.memberships.get_list_companies_by_user(
            context.user_id
        )
        company_briefs: List[CompanyBrief] = []
        for company in companies:
            company_briefs.append(CompanyBrief.model_validate(company))

        permission_list: List[str] = []
        for permission_key in context.permissions:
            permission_list.append(permission_key)

        return MeResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            company_id=context.company_id,
            plan=context.plan_slug,
            permissions=permission_list,
            features=context.features,
            companies=company_briefs,
        )

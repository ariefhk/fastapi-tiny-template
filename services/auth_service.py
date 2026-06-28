import datetime as dt
from typing import Tuple
from uuid import UUID

from fastapi import HTTPException

from commons.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from databases.unit_of_work import UnitOfWork
from models.activity_log_model import ActivityLogAction
from models.auth_identity_model import AuthProviderEnum
from models.session_model import SessionModel
from models.user_model import UserModel
from schemas.requests.auth_request import (
    LoginRequest,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from schemas.responses.user_response import UserResponse


class AuthService:
    def __init__(
        self,
        uow: UnitOfWork,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._uow = uow
        self._ip_address = ip_address
        self._user_agent = user_agent

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _create_session(
        self, user: UserModel
    ) -> Tuple[str, str, SessionModel]:
        """Create a DB session and return (access_token, refresh_token, session)."""
        raw_refresh = generate_refresh_token()
        refresh_hash = hash_refresh_token(raw_refresh)
        expires_at = refresh_token_expires_at()

        session = await self._uow.sessions.create(
            user_id=user.id,
            active_company_id=user.last_active_company_id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
        )
        await self._uow.flush()
        await self._uow.refresh(session)

        access_token = create_access_token(
            user_id=user.id,
            session_id=session.id,
            active_company_id=user.last_active_company_id,
        )
        return access_token, raw_refresh, session

    async def _log(
        self,
        table_name: str,
        table_id: UUID,
        action: ActivityLogAction,
        actor_id: UUID | None = None,
        company_id: UUID | None = None,
        before: dict | None = None,
        after: dict | None = None,
    ) -> None:
        await self._uow.activity_logs.create(
            company_id=company_id,
            actor_id=actor_id,
            table_name=table_name,
            table_id=table_id,
            action=action,
            before=before,
            after=after,
            ip_address=self._ip_address,
            user_agent=self._user_agent,
        )

    # -------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------

    async def register(
        self, body: RegisterRequest
    ) -> Tuple[str, str, UserModel]:
        """
        Register a new user with email + password.

        Creates the user row, a PASSWORD auth identity, and an email verification
        token. Returns (access_token, refresh_token, user).
        """
        existing = await self._uow.users.get_by_email(body.email)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = await self._uow.users.create(email=body.email, name=body.name)
        await self._uow.flush()
        await self._uow.refresh(user)

        await self._uow.auth_identities.create(
            user_id=user.id,
            provider=AuthProviderEnum.PASSWORD,
            password_hash=hash_password(body.password),
            email=body.email,
        )

        # Email verification token — expires in 24 h
        raw_token = generate_refresh_token()
        await self._uow.email_verification_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24),
        )

        access_token, raw_refresh, session = await self._create_session(user)

        await self._log(
            table_name="users",
            table_id=user.id,
            action=ActivityLogAction.CREATE,
            actor_id=user.id,
            after=UserResponse.model_validate(user).model_dump(mode="json"),
        )

        return access_token, raw_refresh, user

    async def login(self, body: LoginRequest) -> Tuple[str, str, UserModel]:
        """
        Authenticate with email + password.

        Returns (access_token, refresh_token, user) or raises 401.
        """
        user = await self._uow.users.get_by_email(body.email)
        identity = None
        if user is not None:
            identity = await self._uow.auth_identities.get_by_user_and_provider(
                user_id=user.id, provider=AuthProviderEnum.PASSWORD
            )

        # Constant-time guard — always call verify_password even on miss
        password_ok = (
            identity is not None
            and identity.password_hash is not None
            and verify_password(body.password, identity.password_hash)
        )
        if user is None or not password_ok:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token, raw_refresh, session = await self._create_session(user)

        await self._log(
            table_name="sessions",
            table_id=session.id,
            action=ActivityLogAction.LOGIN,
            actor_id=user.id,
            company_id=user.last_active_company_id,
        )

        return access_token, raw_refresh, user

    async def refresh(self, raw_refresh_token: str) -> Tuple[str, UserModel]:
        """
        Issue a new access token from a valid refresh token.

        Returns (new_access_token, user) or raises 401.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await self._uow.sessions.get_by_refresh_token_hash(token_hash)
        if session is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        now = dt.datetime.now(dt.timezone.utc)
        if session.expires_at.tzinfo is None:
            expires = session.expires_at.replace(tzinfo=dt.timezone.utc)
        else:
            expires = session.expires_at

        if now > expires:
            await self._uow.sessions.delete(session)
            raise HTTPException(status_code=401, detail="Refresh token expired")

        user = await self._uow.users.get_by_id(session.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        access_token = create_access_token(
            user_id=user.id,
            session_id=session.id,
            active_company_id=session.active_company_id,
        )

        await self._log(
            table_name="sessions",
            table_id=session.id,
            action=ActivityLogAction.REFRESH,
            actor_id=user.id,
            company_id=session.active_company_id,
        )

        return access_token, user

    async def logout(self, session: SessionModel, actor_id: UUID) -> None:
        """Revoke a single session."""
        company_id = session.active_company_id
        session_id = session.id
        await self._uow.sessions.delete(session)
        await self._log(
            table_name="sessions",
            table_id=session_id,
            action=ActivityLogAction.LOGOUT,
            actor_id=actor_id,
            company_id=company_id,
        )

    async def logout_all(self, user_id: UUID, company_id: UUID | None = None) -> None:
        """Revoke all sessions for *user_id*."""
        await self._uow.sessions.delete_by_user_id(user_id)
        await self._log(
            table_name="sessions",
            table_id=user_id,
            action=ActivityLogAction.LOGOUT_ALL,
            actor_id=user_id,
            company_id=company_id,
        )

    async def verify_email(self, body: VerifyEmailRequest) -> UserModel:
        """
        Mark the user's email as verified using the one-time token.

        Raises 400 if the token is invalid, already used, or expired.
        """
        token_hash = hash_refresh_token(body.token)
        token = await self._uow.email_verification_tokens.get_by_token_hash(token_hash)
        if token is None:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        if token.verified_at is not None:
            raise HTTPException(status_code=400, detail="Token already used")

        now = dt.datetime.now(dt.timezone.utc)
        if token.expires_at.tzinfo is None:
            expires = token.expires_at.replace(tzinfo=dt.timezone.utc)
        else:
            expires = token.expires_at

        if now > expires:
            raise HTTPException(status_code=400, detail="Verification token expired")

        await self._uow.email_verification_tokens.update(token, verified_at=now)

        user = await self._uow.users.get_by_id(token.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        await self._uow.users.update(user, email_verified_at=now)
        await self._uow.flush()
        await self._uow.refresh(user)

        await self._log(
            table_name="users",
            table_id=user.id,
            action=ActivityLogAction.UPDATE,
            actor_id=user.id,
            after={"email_verified_at": now.isoformat()},
        )

        return user

    async def request_password_reset(
        self, body: RequestPasswordResetRequest
    ) -> None:
        """
        Create a password reset token for *email*.

        Always returns silently — even if the email is not registered —
        to prevent user enumeration.
        """
        user = await self._uow.users.get_by_email(body.email)
        if user is None:
            return

        raw_token = generate_refresh_token()
        await self._uow.password_reset_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
        )

    async def reset_password(self, body: ResetPasswordRequest) -> None:
        """
        Reset the user's password using a valid one-time token.

        Raises 400 if the token is invalid, already used, or expired.
        """
        token_hash = hash_refresh_token(body.token)
        token = await self._uow.password_reset_tokens.get_by_token_hash(token_hash)
        if token is None:
            raise HTTPException(status_code=400, detail="Invalid reset token")
        if token.used_at is not None:
            raise HTTPException(status_code=400, detail="Token already used")

        now = dt.datetime.now(dt.timezone.utc)
        if token.expires_at.tzinfo is None:
            expires = token.expires_at.replace(tzinfo=dt.timezone.utc)
        else:
            expires = token.expires_at

        if now > expires:
            raise HTTPException(status_code=400, detail="Reset token expired")

        identity = await self._uow.auth_identities.get_by_user_and_provider(
            user_id=token.user_id, provider=AuthProviderEnum.PASSWORD
        )
        if identity is None:
            raise HTTPException(status_code=400, detail="No password login for this account")

        await self._uow.auth_identities.update(
            identity, password_hash=hash_password(body.new_password)
        )
        await self._uow.password_reset_tokens.update(token, used_at=now)

        await self._log(
            table_name="password_reset_tokens",
            table_id=token.id,
            action=ActivityLogAction.UPDATE,
            actor_id=token.user_id,
        )

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from databases.session import get_db_session
from repositories.access_repository import AccessRepository
from repositories.activity_log_repository import ActivityLogRepository
from repositories.auth_identity_repository import AuthIdentityRepository
from repositories.company_repository import CompanyRepository
from repositories.email_verification_token_repository import (
    EmailVerificationTokenRepository,
)
from repositories.feature_repository import FeatureRepository
from repositories.invitation_repository import InvitationRepository
from repositories.membership_permission_override_repository import (
    MembershipPermissionOverrideRepository,
)
from repositories.membership_repository import MembershipRepository
from repositories.membership_role_repository import MembershipRoleRepository
from repositories.password_reset_token_repository import PasswordResetTokenRepository
from repositories.permission_repository import PermissionRepository
from repositories.plan_feature_repository import PlanFeatureRepository
from repositories.plan_repository import PlanRepository
from repositories.role_permission_repository import RolePermissionRepository
from repositories.role_repository import RoleRepository
from repositories.session_repository import SessionRepository
from repositories.subscription_repository import SubscriptionRepository
from repositories.user_repository import UserRepository
from repositories.webhook_event_repository import WebhookEventRepository


class UnitOfWork:
    """Wraps a single database session for use across the service layer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.access = AccessRepository(session)
        self.users = UserRepository(session)
        self.companies = CompanyRepository(session)
        self.activity_logs = ActivityLogRepository(session)
        self.auth_identities = AuthIdentityRepository(session)
        self.email_verification_tokens = EmailVerificationTokenRepository(session)
        self.features = FeatureRepository(session)
        self.invitations = InvitationRepository(session)
        self.memberships = MembershipRepository(session)
        self.membership_permission_overrides = MembershipPermissionOverrideRepository(
            session
        )
        self.membership_roles = MembershipRoleRepository(session)
        self.password_reset_tokens = PasswordResetTokenRepository(session)
        self.permissions = PermissionRepository(session)
        self.plan_features = PlanFeatureRepository(session)
        self.plans = PlanRepository(session)
        self.roles = RoleRepository(session)
        self.role_permissions = RolePermissionRepository(session)
        self.sessions = SessionRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.webhook_events = WebhookEventRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def refresh(self, instance: Any) -> None:
        await self._session.refresh(instance)


async def uow_deps() -> AsyncIterator[UnitOfWork]:
    """
    FastAPI dependency: yields a UnitOfWork, commits on success, rolls back on error.
    """
    session = await get_db_session()
    async with session:
        uow = UnitOfWork(
            session,
        )
        try:
            yield uow
            await uow.commit()
        except Exception:
            await uow.rollback()
            raise


@asynccontextmanager
async def uow_ctx() -> AsyncIterator[UnitOfWork]:
    """
    Context manager for background jobs and scripts (outside a FastAPI request).
    """
    session = await get_db_session()
    async with session:
        uow = UnitOfWork(
            session,
        )
        try:
            yield uow
            await uow.commit()
        except Exception:
            await uow.rollback()
            raise

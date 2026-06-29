import uuid
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feature_model import FeatureModel
from models.membership_permission_override_model import (
    MembershipPermissionOverrideModel,
    OverrideEffectEnum,
)
from models.membership_role_model import MembershipRoleModel
from models.permission_model import PermissionModel
from models.plan_feature_model import PlanFeatureModel
from models.plan_model import PlanModel
from models.role_permission_model import RolePermissionModel
from models.subscription_model import SubscriptionModel


class AccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_permissions(self, membership_id: uuid.UUID) -> set:
        """Return the effective permission keys for a membership.

        Collects permissions granted via roles, then applies overrides:
        ALLOW overrides add keys not covered by any role; DENY overrides
        remove keys regardless of role grants.
        """
        role_perm_stmt = (
            select(PermissionModel.key)
            .select_from(MembershipRoleModel)
            .join(RolePermissionModel, RolePermissionModel.role_id == MembershipRoleModel.role_id)
            .join(PermissionModel, PermissionModel.id == RolePermissionModel.permission_id)
            .where(MembershipRoleModel.membership_id == membership_id)
        )
        role_perm_result = await self._session.execute(role_perm_stmt)
        permissions: set = set()
        for row in role_perm_result.all():
            permissions.add(row[0])

        override_stmt = (
            select(PermissionModel.key, MembershipPermissionOverrideModel.effect)
            .select_from(MembershipPermissionOverrideModel)
            .join(
                PermissionModel,
                PermissionModel.id == MembershipPermissionOverrideModel.permission_id,
            )
            .where(MembershipPermissionOverrideModel.membership_id == membership_id)
        )
        override_result = await self._session.execute(override_stmt)
        override_rows = override_result.all()

        for row in override_rows:
            if row[1] == OverrideEffectEnum.ALLOW.value:
                permissions.add(row[0])

        for row in override_rows:
            if row[1] == OverrideEffectEnum.DENY.value:
                permissions.discard(row[0])

        return permissions

    async def resolve_entitlements(self, company_id: uuid.UUID) -> Tuple[Optional[str], dict]:
        """Return the active plan slug and feature entitlements for a company.

        Returns ``(None, {})`` when the company has no active subscription or
        the subscription is not linked to a plan. Otherwise returns the plan
        slug and a mapping of ``feature_key -> {enabled, limit}``.
        """
        plan_stmt = (
            select(PlanModel.id, PlanModel.slug)
            .select_from(SubscriptionModel)
            .join(PlanModel, PlanModel.id == SubscriptionModel.plan_id)
            .where(SubscriptionModel.company_id == company_id)
        )
        plan_result = await self._session.execute(plan_stmt)
        plan_row = plan_result.first()
        if plan_row is None:
            return None, {}

        plan_id = plan_row[0]
        plan_slug = plan_row[1]

        feature_stmt = (
            select(FeatureModel.key, PlanFeatureModel.enabled, PlanFeatureModel.limit_value)
            .select_from(PlanFeatureModel)
            .join(FeatureModel, FeatureModel.id == PlanFeatureModel.feature_id)
            .where(PlanFeatureModel.plan_id == plan_id)
        )
        feature_result = await self._session.execute(feature_stmt)
        features: dict = {}
        for row in feature_result.all():
            features[row[0]] = {"enabled": row[1], "limit": row[2]}

        return plan_slug, features

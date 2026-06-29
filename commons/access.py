import uuid
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from commons.security import decode_access_token
from databases.unit_of_work import UnitOfWork, uow_deps


@dataclass
class AccessContext:
    user_id: uuid.UUID
    company_id: uuid.UUID
    membership_id: uuid.UUID
    permissions: set = field(default_factory=set)
    plan_slug: Optional[str] = None
    features: dict = field(default_factory=dict)

    def can(self, permission_key: str) -> bool:
        return permission_key in self.permissions

    def has_feature(self, feature_key: str) -> bool:
        entry = self.features.get(feature_key)
        if entry is None:
            return False
        return entry.get("enabled", False) is True

    def limit(self, feature_key: str) -> Optional[int]:
        entry = self.features.get(feature_key)
        if entry is None:
            return None
        return entry.get("limit")


async def get_access_context(
    request: Request,
    uow: UnitOfWork = Depends(uow_deps),
) -> AccessContext:
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )

    token = auth_header.removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user_id = uuid.UUID(claims["sub"])
    active_company_id = claims.get("active_company_id")
    if active_company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No active company"
        )

    company_id = uuid.UUID(active_company_id)

    membership = await uow.memberships.get_by_user_and_company(user_id, company_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No membership in active company",
        )

    permissions = await uow.access.resolve_permissions(membership.id)
    entitlements = await uow.access.resolve_entitlements(company_id)
    plan_slug = entitlements[0]
    features = entitlements[1]

    context = AccessContext(
        user_id=user_id,
        company_id=company_id,
        membership_id=membership.id,
        permissions=permissions,
        plan_slug=plan_slug,
        features=features,
    )
    return context


def require_permission(permission_key: str):
    async def dependency(
        context: AccessContext = Depends(get_access_context),
    ) -> AccessContext:
        if context.can(permission_key) is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"reason": "permission", "need": permission_key},
            )
        return context

    return dependency


def require_feature(feature_key: str):
    async def dependency(
        context: AccessContext = Depends(get_access_context),
    ) -> AccessContext:
        if context.has_feature(feature_key) is False:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"reason": "upgrade", "feature": feature_key},
            )
        return context

    return dependency

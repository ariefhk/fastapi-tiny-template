from fastapi import APIRouter

from routers.v1 import (
    activity_log_router,
    auth_router,
    company_router,
    feature_router,
    membership_permission_override_router,
    membership_role_router,
    membership_router,
    role_permission_router,
    role_router,
    session_router,
    user_router,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router.router)
v1_router.include_router(activity_log_router.router)
v1_router.include_router(company_router.router)
v1_router.include_router(feature_router.router)
v1_router.include_router(membership_router.router)
v1_router.include_router(membership_permission_override_router.router)
v1_router.include_router(membership_role_router.router)
v1_router.include_router(role_router.router)
v1_router.include_router(role_permission_router.router)
v1_router.include_router(session_router.router)
v1_router.include_router(user_router.router)

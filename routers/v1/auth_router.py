from fastapi import APIRouter, Depends, Request

from commons.deps import CurrentAuth, get_current_auth
from commons.request import request_context
from commons.response import APIResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.auth_request import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from schemas.responses.auth_response import AccessTokenResponse, TokenResponse
from schemas.responses.user_response import UserResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[TokenResponse],
    status_code=201,
)
async def register(
    request: Request,
    body: RegisterRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Register a new account with email + password. Returns tokens and the created user."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    access_token, refresh_token, user = await service.register(body)
    return APIResponse.success(
        request,
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        ),
        message="Registration successful",
        status_code=201,
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    status_code=200,
)
async def login(
    request: Request,
    body: LoginRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Authenticate with email + password. Returns access and refresh tokens."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    access_token, refresh_token, user = await service.login(body)
    return APIResponse.success(
        request,
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        ),
        status_code=200,
    )


@router.post(
    "/refresh",
    response_model=SuccessResponse[AccessTokenResponse],
    status_code=200,
)
async def refresh(
    request: Request,
    body: RefreshTokenRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Issue a new access token from a valid refresh token."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    access_token, _ = await service.refresh(body.refresh_token)
    return APIResponse.success(
        request,
        AccessTokenResponse(access_token=access_token),
        status_code=200,
    )


@router.post(
    "/logout",
    response_model=SuccessResponse[None],
    status_code=200,
)
async def logout(
    request: Request,
    uow: UnitOfWork = Depends(uow_deps),
    current: CurrentAuth = Depends(get_current_auth),
):
    """Revoke the current session. Requires a valid Bearer token."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    await service.logout(session=current.session, actor_id=current.user.id)
    return APIResponse.success(request, None, message="Logged out", status_code=200)


@router.post(
    "/logout-all",
    response_model=SuccessResponse[None],
    status_code=200,
)
async def logout_all(
    request: Request,
    uow: UnitOfWork = Depends(uow_deps),
    current: CurrentAuth = Depends(get_current_auth),
):
    """Revoke all sessions for the authenticated user. Requires a valid Bearer token."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    await service.logout_all(
        user_id=current.user.id,
        company_id=current.session.active_company_id,
    )
    return APIResponse.success(
        request, None, message="All sessions revoked", status_code=200
    )


@router.post(
    "/verify-email",
    response_model=SuccessResponse[UserResponse],
    status_code=200,
)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Verify email address using the one-time token sent during registration."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    user = await service.verify_email(body)
    return APIResponse.success(
        request,
        UserResponse.model_validate(user),
        message="Email verified",
        status_code=200,
    )


@router.post(
    "/request-password-reset",
    response_model=SuccessResponse[None],
    status_code=200,
)
async def request_password_reset(
    request: Request,
    body: RequestPasswordResetRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """
    Send a password reset link to the given email.
    Always returns 200 regardless of whether the email exists (prevents enumeration).
    """
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    await service.request_password_reset(body)
    return APIResponse.success(
        request,
        None,
        message="If this email is registered you will receive a reset link",
        status_code=200,
    )


@router.post(
    "/reset-password",
    response_model=SuccessResponse[None],
    status_code=200,
)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Reset the account password using a valid one-time reset token."""
    ctx = request_context(request)
    service = AuthService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    await service.reset_password(body)
    return APIResponse.success(
        request, None, message="Password reset successful", status_code=200
    )

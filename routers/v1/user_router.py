from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.request import request_context
from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.user_request import (
    UserCreateRequest,
    UserFilterRequest,
    UserUpdateRequest,
)
from schemas.responses.user_response import UserResponse
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=SuccessListResponse[UserResponse],
    status_code=200,
)
async def get_all(
    request: Request,
    email: str | None = Query(None),
    name: str | None = Query(None),
    mfa_enabled: bool | None = Query(None),
    email_verified: bool | None = Query(None),
    last_active_company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of users, optionally filtered by any combination of fields."""
    filters = UserFilterRequest(
        email=email,
        name=name,
        mfa_enabled=mfa_enabled,
        email_verified=email_verified,
        last_active_company_id=last_active_company_id,
    )
    ctx = request_context(request)
    service = UserService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request,
        items,
        page=page,
        limit=limit,
        total_items=total,
        status_code=200,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[UserResponse],
    status_code=200,
)
async def get_by_id(
    request: Request,
    id: UUID,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a single user by id. Returns 404 if not found."""
    ctx = request_context(request)
    service = UserService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    user = await service.get_by_id(id)
    return APIResponse.success(request, user, status_code=200)


@router.post(
    "",
    response_model=SuccessResponse[UserResponse],
    status_code=201,
)
async def create(
    request: Request,
    body: UserCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new user and return the created record."""
    ctx = request_context(request)
    service = UserService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    user = await service.create(body)
    return APIResponse.success(request, user, message="User created", status_code=201)


@router.patch(
    "/{id}",
    response_model=SuccessResponse[UserResponse],
    status_code=200,
)
async def update(
    request: Request,
    id: UUID,
    body: UserUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a user. Only fields present in the body are changed."""
    ctx = request_context(request)
    service = UserService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    user = await service.update(id, body)
    return APIResponse.success(request, user, status_code=200)


@router.delete(
    "/{id}",
    response_model=SuccessResponse[None],
    status_code=200,
)
async def delete(
    request: Request,
    id: UUID,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Hard-delete a user by id. Returns 404 if not found."""
    ctx = request_context(request)
    service = UserService(uow, ip_address=ctx["ip"], user_agent=ctx["ua"])
    await service.delete(id)
    return APIResponse.success(request, None, message="User deleted", status_code=200)

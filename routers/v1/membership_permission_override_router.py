from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from models.membership_permission_override_model import OverrideEffectEnum
from schemas.requests.membership_permission_override_request import (
    MembershipPermissionOverrideCreateRequest,
    MembershipPermissionOverrideFilterRequest,
    MembershipPermissionOverrideUpdateRequest,
)
from schemas.responses.membership_permission_override_response import (
    MembershipPermissionOverrideResponse,
)
from services.membership_permission_override_service import (
    MembershipPermissionOverrideService,
)

router = APIRouter(
    prefix="/membership-permission-overrides", tags=["Membership Permission Overrides"]
)


@router.get(
    "",
    response_model=SuccessListResponse[MembershipPermissionOverrideResponse],
    status_code=200,
)
async def get_all(
    request: Request,
    membership_id: UUID | None = Query(None),
    permission_id: UUID | None = Query(None),
    effect: OverrideEffectEnum | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of permission overrides, optionally filtered by membership, permission, or effect."""
    filters = MembershipPermissionOverrideFilterRequest(
        membership_id=membership_id, permission_id=permission_id, effect=effect
    )
    service = MembershipPermissionOverrideService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[MembershipPermissionOverrideResponse],
    status_code=200,
)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single permission override by id. Returns 404 if not found."""
    service = MembershipPermissionOverrideService(uow)
    override = await service.get_by_id(id)
    return APIResponse.success(request, override, status_code=200)


@router.post(
    "",
    response_model=SuccessResponse[MembershipPermissionOverrideResponse],
    status_code=201,
)
async def create(
    request: Request,
    body: MembershipPermissionOverrideCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new permission override and return the created record."""
    service = MembershipPermissionOverrideService(uow)
    override = await service.create(body)
    return APIResponse.success(
        request, override, message="Permission override created", status_code=201
    )


@router.patch(
    "/{id}",
    response_model=SuccessResponse[MembershipPermissionOverrideResponse],
    status_code=200,
)
async def update(
    request: Request,
    id: UUID,
    body: MembershipPermissionOverrideUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a permission override. Only fields present in the body are changed."""
    service = MembershipPermissionOverrideService(uow)
    override = await service.update(id, body)
    return APIResponse.success(request, override, status_code=200)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a permission override by id. Returns 404 if not found."""
    service = MembershipPermissionOverrideService(uow)
    await service.delete(id)
    return APIResponse.success(
        request, None, message="Permission override deleted", status_code=200
    )

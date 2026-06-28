from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.membership_role_request import (
    MembershipRoleCreateRequest,
    MembershipRoleFilterRequest,
)
from schemas.responses.membership_role_response import MembershipRoleResponse
from services.membership_role_service import MembershipRoleService

router = APIRouter(prefix="/membership-roles", tags=["Membership Roles"])


@router.get("", response_model=SuccessListResponse[MembershipRoleResponse], status_code=200)
async def get_all(
    request: Request,
    membership_id: UUID | None = Query(None),
    role_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of membership roles, optionally filtered by membership or role."""
    filters = MembershipRoleFilterRequest(membership_id=membership_id, role_id=role_id)
    service = MembershipRoleService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/{id}", response_model=SuccessResponse[MembershipRoleResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single membership role by id. Returns 404 if not found."""
    service = MembershipRoleService(uow)
    mr = await service.get_by_id(id)
    return APIResponse.success(request, mr, status_code=200)


@router.post("", response_model=SuccessResponse[MembershipRoleResponse], status_code=201)
async def create(
    request: Request,
    body: MembershipRoleCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Assign a role to a membership and return the created link."""
    service = MembershipRoleService(uow)
    mr = await service.create(body)
    return APIResponse.success(
        request, mr, message="Membership role created", status_code=201
    )


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a membership role link by id. Returns 404 if not found."""
    service = MembershipRoleService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Membership role deleted", status_code=200)

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from models.membership_model import MembershipStatusEnum
from schemas.requests.membership_request import (
    MembershipCreateRequest,
    MembershipFilterRequest,
    MembershipUpdateRequest,
)
from schemas.responses.membership_response import MembershipResponse
from services.membership_service import MembershipService

router = APIRouter(prefix="/memberships", tags=["Memberships"])


@router.get("", response_model=SuccessListResponse[MembershipResponse], status_code=200)
async def get_all(
    request: Request,
    user_id: UUID | None = Query(None),
    company_id: UUID | None = Query(None),
    status: MembershipStatusEnum | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of memberships, optionally filtered by user, company, or status."""
    filters = MembershipFilterRequest(user_id=user_id, company_id=company_id, status=status)
    service = MembershipService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/{id}", response_model=SuccessResponse[MembershipResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single membership by id. Returns 404 if not found."""
    service = MembershipService(uow)
    membership = await service.get_by_id(id)
    return APIResponse.success(request, membership, status_code=200)


@router.post("", response_model=SuccessResponse[MembershipResponse], status_code=201)
async def create(
    request: Request,
    body: MembershipCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new membership and return the created record."""
    service = MembershipService(uow)
    membership = await service.create(body)
    return APIResponse.success(
        request, membership, message="Membership created", status_code=201
    )


@router.patch("/{id}", response_model=SuccessResponse[MembershipResponse], status_code=200)
async def update(
    request: Request,
    id: UUID,
    body: MembershipUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a membership. Only fields present in the body are changed."""
    service = MembershipService(uow)
    membership = await service.update(id, body)
    return APIResponse.success(request, membership, status_code=200)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a membership by id. Returns 404 if not found."""
    service = MembershipService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Membership deleted", status_code=200)

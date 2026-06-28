from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.role_request import (
    RoleCreateRequest,
    RoleFilterRequest,
    RoleUpdateRequest,
)
from schemas.responses.role_response import RoleResponse
from services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=SuccessListResponse[RoleResponse], status_code=200)
async def get_all(
    request: Request,
    company_id: UUID | None = Query(None),
    name: str | None = Query(None),
    slug: str | None = Query(None),
    is_system: bool | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of roles, optionally filtered by company, name, slug, or is_system."""
    filters = RoleFilterRequest(company_id=company_id, name=name, slug=slug, is_system=is_system)
    service = RoleService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/{id}", response_model=SuccessResponse[RoleResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single role by id. Returns 404 if not found."""
    service = RoleService(uow)
    role = await service.get_by_id(id)
    return APIResponse.success(request, role, status_code=200)


@router.post("", response_model=SuccessResponse[RoleResponse], status_code=201)
async def create(
    request: Request,
    body: RoleCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new role and return the created record."""
    service = RoleService(uow)
    role = await service.create(body)
    return APIResponse.success(request, role, message="Role created", status_code=201)


@router.patch("/{id}", response_model=SuccessResponse[RoleResponse], status_code=200)
async def update(
    request: Request,
    id: UUID,
    body: RoleUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a role. Only fields present in the body are changed."""
    service = RoleService(uow)
    role = await service.update(id, body)
    return APIResponse.success(request, role, status_code=200)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a role by id. Returns 404 if not found."""
    service = RoleService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Role deleted", status_code=200)

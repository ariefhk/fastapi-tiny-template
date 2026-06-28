from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.role_permission_request import (
    RolePermissionCreateRequest,
    RolePermissionFilterRequest,
)
from schemas.responses.role_permission_response import RolePermissionResponse
from services.role_permission_service import RolePermissionService

router = APIRouter(prefix="/role-permissions", tags=["Role Permissions"])


@router.get("", response_model=SuccessListResponse[RolePermissionResponse], status_code=200)
async def get_all(
    request: Request,
    role_id: UUID | None = Query(None),
    permission_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of role permissions, optionally filtered by role or permission."""
    filters = RolePermissionFilterRequest(role_id=role_id, permission_id=permission_id)
    service = RolePermissionService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/{id}", response_model=SuccessResponse[RolePermissionResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single role permission by id. Returns 404 if not found."""
    service = RolePermissionService(uow)
    rp = await service.get_by_id(id)
    return APIResponse.success(request, rp, status_code=200)


@router.post("", response_model=SuccessResponse[RolePermissionResponse], status_code=201)
async def create(
    request: Request,
    body: RolePermissionCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Assign a permission to a role and return the created link."""
    service = RolePermissionService(uow)
    rp = await service.create(body)
    return APIResponse.success(request, rp, message="Role permission created", status_code=201)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a role permission link by id. Returns 404 if not found."""
    service = RolePermissionService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Role permission deleted", status_code=200)

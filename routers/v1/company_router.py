from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.company_request import (
    CompanyCreateRequest,
    CompanyFilterRequest,
    CompanyUpdateRequest,
)
from schemas.responses.company_response import CompanyResponse
from services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=SuccessListResponse[CompanyResponse], status_code=200)
async def get_all(
    request: Request,
    name: str | None = Query(None),
    slug: str | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of companies, optionally filtered by name, slug, or owner."""
    filters = CompanyFilterRequest(name=name, slug=slug, owner_user_id=owner_user_id)
    service = CompanyService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/by-slug/{slug}", response_model=SuccessResponse[CompanyResponse], status_code=200)
async def get_by_slug(request: Request, slug: str, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single company by slug. Returns 404 if not found."""
    service = CompanyService(uow)
    company = await service.get_by_slug(slug)
    return APIResponse.success(request, company, status_code=200)


@router.get("/{id}", response_model=SuccessResponse[CompanyResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single company by id. Returns 404 if not found."""
    service = CompanyService(uow)
    company = await service.get_by_id(id)
    return APIResponse.success(request, company, status_code=200)


@router.post("", response_model=SuccessResponse[CompanyResponse], status_code=201)
async def create(
    request: Request,
    body: CompanyCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new company and return the created record."""
    service = CompanyService(uow)
    company = await service.create(body)
    return APIResponse.success(request, company, message="Company created", status_code=201)


@router.patch("/{id}", response_model=SuccessResponse[CompanyResponse], status_code=200)
async def update(
    request: Request,
    id: UUID,
    body: CompanyUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a company. Only fields present in the body are changed."""
    service = CompanyService(uow)
    company = await service.update(id, body)
    return APIResponse.success(request, company, status_code=200)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a company by id. Returns 404 if not found."""
    service = CompanyService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Company deleted", status_code=200)

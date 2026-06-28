from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from models.feature_model import FeatureKindEnum
from schemas.requests.feature_request import (
    FeatureCreateRequest,
    FeatureFilterRequest,
    FeatureUpdateRequest,
)
from schemas.responses.feature_response import FeatureResponse
from services.feature_service import FeatureService

router = APIRouter(prefix="/features", tags=["Features"])


@router.get("", response_model=SuccessListResponse[FeatureResponse], status_code=200)
async def get_all(
    request: Request,
    key: str | None = Query(None),
    name: str | None = Query(None),
    kind: FeatureKindEnum | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of features, optionally filtered by key, name, or kind."""
    filters = FeatureFilterRequest(key=key, name=name, kind=kind)
    service = FeatureService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/by-key/{key}", response_model=SuccessResponse[FeatureResponse], status_code=200)
async def get_by_key(request: Request, key: str, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single feature by unique key. Returns 404 if not found."""
    service = FeatureService(uow)
    feature = await service.get_by_key(key)
    return APIResponse.success(request, feature, status_code=200)


@router.get("/{id}", response_model=SuccessResponse[FeatureResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single feature by id. Returns 404 if not found."""
    service = FeatureService(uow)
    feature = await service.get_by_id(id)
    return APIResponse.success(request, feature, status_code=200)


@router.post("", response_model=SuccessResponse[FeatureResponse], status_code=201)
async def create(
    request: Request,
    body: FeatureCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new feature and return the created record."""
    service = FeatureService(uow)
    feature = await service.create(body)
    return APIResponse.success(request, feature, message="Feature created", status_code=201)


@router.patch("/{id}", response_model=SuccessResponse[FeatureResponse], status_code=200)
async def update(
    request: Request,
    id: UUID,
    body: FeatureUpdateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Partially update a feature. Only fields present in the body are changed."""
    service = FeatureService(uow)
    feature = await service.update(id, body)
    return APIResponse.success(request, feature, status_code=200)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a feature by id. Returns 404 if not found."""
    service = FeatureService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Feature deleted", status_code=200)

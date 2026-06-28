from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from schemas.requests.session_request import SessionCreateRequest, SessionFilterRequest
from schemas.responses.session_response import SessionResponse
from services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=SuccessListResponse[SessionResponse], status_code=200)
async def get_all(
    request: Request,
    user_id: UUID | None = Query(None),
    active_company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    """Return a paginated list of sessions, optionally filtered by user or company."""
    filters = SessionFilterRequest(user_id=user_id, active_company_id=active_company_id)
    service = SessionService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )


@router.get("/{id}", response_model=SuccessResponse[SessionResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Return a single session by id. Returns 404 if not found."""
    service = SessionService(uow)
    session = await service.get_by_id(id)
    return APIResponse.success(request, session, status_code=200)


@router.post("", response_model=SuccessResponse[SessionResponse], status_code=201)
async def create(
    request: Request,
    body: SessionCreateRequest,
    uow: UnitOfWork = Depends(uow_deps),
):
    """Create a new session and return the created record."""
    service = SessionService(uow)
    session = await service.create(body)
    return APIResponse.success(request, session, message="Session created", status_code=201)


@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    """Hard-delete a session by id. Returns 404 if not found."""
    service = SessionService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Session deleted", status_code=200)

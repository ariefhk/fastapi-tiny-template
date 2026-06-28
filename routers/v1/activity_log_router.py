from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request

from commons.response import APIResponse, SuccessListResponse, SuccessResponse
from databases.unit_of_work import UnitOfWork, uow_deps
from models.activity_log_model import ActivityLogAction
from schemas.requests.activity_log_request import ActivityLogFilterRequest
from schemas.responses.activity_log_response import ActivityLogResponse
from services.activity_log_service import ActivityLogService

router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])


@router.get(
    "",
    response_model=SuccessListResponse[ActivityLogResponse],
    status_code=200,
)
async def get_all(
    request: Request,
    company_id: UUID | None = Query(None),
    actor_id: UUID | None = Query(None),
    action: ActivityLogAction | None = Query(None),
    table_name: str | None = Query(None),
    table_id: UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    filters = ActivityLogFilterRequest(
        company_id=company_id,
        actor_id=actor_id,
        action=action,
        table_name=table_name,
        table_id=table_id,
        from_date=from_date,
        to_date=to_date,
    )
    service = ActivityLogService(uow)
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
    "/table-names",
    response_model=SuccessResponse[list[str]],
    status_code=200,
)
async def get_distinct_table_names(
    request: Request,
    uow: UnitOfWork = Depends(uow_deps),
):
    service = ActivityLogService(uow)
    table_names = await service.get_distinct_table_names()
    return APIResponse.success(request, table_names, status_code=200)


@router.get(
    "/{id}",
    response_model=SuccessResponse[ActivityLogResponse],
    status_code=200,
)
async def get_by_id(
    request: Request,
    id: UUID,
    uow: UnitOfWork = Depends(uow_deps),
):
    service = ActivityLogService(uow)
    activity = await service.get_by_id(id)
    return APIResponse.success(request, activity, status_code=200)


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
    service = ActivityLogService(uow)
    await service.delete(id)
    return APIResponse.success(
        request,
        None,
        message="Activity log deleted",
        status_code=200,
    )


@router.post(
    "/delete-all",
    response_model=SuccessResponse[dict],
    status_code=200,
)
async def delete_all(
    request: Request,
    filters: ActivityLogFilterRequest = Body(default=None),
    uow: UnitOfWork = Depends(uow_deps),
):
    service = ActivityLogService(uow)
    deleted = await service.delete_all(filters)
    return APIResponse.success(
        request,
        {"deleted": deleted},
        message=f"{deleted} activity log(s) deleted",
        status_code=200,
    )

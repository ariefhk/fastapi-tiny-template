"""Standard API response envelopes.

Every endpoint in the project wraps its payload in one of three shapes so
that frontends can rely on a single deserialization path:

    Success (single)
    {
        "status_code": 200,
        "method": "GET",
        "path": "/api/v1/items/1",
        "message": "OK",
        "data": { ... }
    }

    Success (list, paginated)
    {
        "status_code": 200,
        "method": "GET",
        "path": "/api/v1/items",
        "message": "OK",
        "data": [ ... ],
        "meta": {
            "page": 1,
            "limit": 10,
            "total_items": 123,
            "total_pages": 13,
            "has_next_page": true,
            "has_prev_page": false
        }
    }

    Error
    {
        "status_code": 404,
        "method": "GET",
        "path": "/api/v1/items/999",
        "message": "Item 999 not found",
        "error": {
            "code": "ITEM_NOT_FOUND",
            "details": []
        }
    }
"""

from math import ceil
from typing import Any, Generic, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    """Pagination metadata included in every list response."""

    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next_page: bool
    has_prev_page: bool


class SuccessResponse(BaseModel, Generic[T]):
    status_code: int
    method: str
    path: str
    message: str
    data: T


class SuccessListResponse(BaseModel, Generic[T]):
    status_code: int
    method: str
    path: str
    message: str
    data: list[T]
    meta: Meta


class ErrorDetail(BaseModel):
    code: str
    details: list[Any] = []


class ErrorResponse(BaseModel):
    status_code: int
    method: str
    path: str
    message: str
    error: ErrorDetail


def _build_meta(*, page: int, limit: int, total_items: int) -> Meta:
    """Compute the meta block from the page/limit/total triplet."""
    if limit > 0 and total_items > 0:
        total_pages = ceil(total_items / limit)
    else:
        total_pages = 0

    if page < total_pages:
        has_next_page = True
    else:
        has_next_page = False

    if page > 1 and total_pages > 0:
        has_prev_page = True
    else:
        has_prev_page = False

    return Meta(
        page=page,
        limit=limit,
        total_items=total_items,
        total_pages=total_pages,
        has_next_page=has_next_page,
        has_prev_page=has_prev_page,
    )


class APIResponse:
    """Factories for the three response envelopes.

    Success helpers return Pydantic models so endpoints can declare
    ``response_model`` and get accurate OpenAPI docs. The error helper
    returns ``JSONResponse`` because exception handlers are required to
    return ``Response`` objects.

    NOTE on status codes: the ``status_code`` field in the body must match
    the HTTP status FastAPI sends. For success helpers, the route's
    ``status_code=`` decorator is the source of truth for the HTTP header,
    and you must pass the same value here so the body field matches. For
    the error helper, both the body and the actual HTTP status come from
    the ``status_code`` argument, so they are always in sync.
    """

    @staticmethod
    def success(
        request: Request,
        data: T,
        *,
        message: str = "OK",
        status_code: int = 200,
    ) -> "SuccessResponse[T]":
        return SuccessResponse[T](
            status_code=status_code,
            method=request.method,
            path=request.url.path,
            message=message,
            data=data,
        )

    @staticmethod
    def success_list(
        request: Request,
        items: list,
        *,
        page: int,
        limit: int,
        total_items: int,
        message: str = "OK",
        status_code: int = 200,
    ) -> "SuccessListResponse":
        meta = _build_meta(page=page, limit=limit, total_items=total_items)
        return SuccessListResponse(
            meta=meta,
            status_code=status_code,
            method=request.method,
            path=request.url.path,
            message=message,
            data=items,
        )

    @staticmethod
    def error(
        request: Request,
        *,
        message: str,
        code: str,
        details: list[Any] | None = None,
        status_code: int = 400,
    ) -> JSONResponse:
        if details is None:
            safe_details: list[Any] = []
        else:
            safe_details = details
        body = ErrorResponse(
            status_code=status_code,
            method=request.method,
            path=request.url.path,
            message=message,
            error=ErrorDetail(code=code, details=safe_details),
        )
        return JSONResponse(
            content=body.model_dump(),
            status_code=status_code,
        )

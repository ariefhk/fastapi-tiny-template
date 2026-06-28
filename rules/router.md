# Router Rules

## Structure

Every router module follows this layout:

```python
router = APIRouter(prefix="/resource-name", tags=["Resource Name"])

# 1. list endpoint    GET    ""
# 2. special GETs     GET    "/sub-path"   (declare before /{id} to avoid param collision)
# 3. get by id        GET    "/{id}"
# 4. create           POST   ""
# 5. update           PATCH  "/{id}"
# 6. delete           DELETE "/{id}"
# 7. bulk operations  POST   "/action-name"
```

---

## Router declaration

```python
router = APIRouter(prefix="/resource-name", tags=["Resource Name"])
```

Register in `routers/v1/router.py`:

```python
from routers.v1 import xxx_router
v1_router.include_router(xxx_router.router)
```

---

## Service instantiation

Instantiate the service inside each endpoint — never at module level.

```python
service = XxxService(uow)
```

---

## Response envelopes

Always wrap returns in `APIResponse`. Pass `status_code` to both the decorator
and the `APIResponse` call so the HTTP header and body field stay in sync.

| Shape | Use when | Helper |
| --- | --- | --- |
| `SuccessResponse[T]` | single object or scalar | `APIResponse.success()` |
| `SuccessListResponse[T]` | paginated list | `APIResponse.success_list()` |
| `SuccessResponse[None]` | delete with no payload | `APIResponse.success(..., data=None)` |
| `SuccessResponse[dict]` | bulk op with count | `APIResponse.success(..., data={"deleted": n})` |

Errors are not handled inline — raise `HTTPException` and let the global registry
in `exceptions/registry.py` return the `ErrorResponse` shape.

---

## GET list endpoint

Declare filter fields explicitly with `Query()` — do not use `Depends(FilterRequest)`.
Build the filter object manually inside the handler.
Keep `page` and `limit` as `Query` params.

```python
@router.get("", response_model=SuccessListResponse[XxxResponse], status_code=200)
async def get_all(
    request: Request,
    field_a: str | None = Query(None),
    field_b: UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    uow: UnitOfWork = Depends(uow_deps),
):
    filters = XxxFilterRequest(
        field_a=field_a,
        field_b=field_b,
        from_date=from_date,
        to_date=to_date,
    )
    service = XxxService(uow)
    items, total = await service.get_all(filters, page=page, limit=limit)
    return APIResponse.success_list(
        request, items, page=page, limit=limit, total_items=total, status_code=200
    )
```

---

## GET single endpoint

```python
@router.get("/{id}", response_model=SuccessResponse[XxxResponse], status_code=200)
async def get_by_id(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    service = XxxService(uow)
    obj = await service.get_by_id(id)
    return APIResponse.success(request, obj, status_code=200)
```

---

## DELETE single endpoint

```python
@router.delete("/{id}", response_model=SuccessResponse[None], status_code=200)
async def delete(request: Request, id: UUID, uow: UnitOfWork = Depends(uow_deps)):
    service = XxxService(uow)
    await service.delete(id)
    return APIResponse.success(request, None, message="Xxx deleted", status_code=200)
```

---

## Bulk operations (POST)

Use `POST /action-name` for operations that take a large body (bulk delete, bulk update).
Accept the filter/body as `Body(default=None)` so the endpoint works with or without a payload.

```python
@router.post("/delete-all", response_model=SuccessResponse[dict], status_code=200)
async def delete_all(
    request: Request,
    filters: XxxFilterRequest = Body(default=None),
    uow: UnitOfWork = Depends(uow_deps),
):
    service = XxxService(uow)
    deleted = await service.delete_all(filters)
    return APIResponse.success(
        request,
        {"deleted": deleted},
        message=f"{deleted} record(s) deleted",
        status_code=200,
    )
```

---

## Docstrings

Every endpoint function gets a single-line docstring. FastAPI uses it as the OpenAPI
operation description, so write it from the API consumer's perspective.

| Endpoint | What to document |
|---|---|
| `GET ""` | "Return a paginated list … optionally filtered by …" |
| `GET "/{id}"` | "Return a single … Returns 404 if not found." |
| `POST ""` | "Create a new … and return the created record." |
| `PATCH "/{id}"` | "Partially update … Only fields present in the body are changed." |
| `DELETE "/{id}"` | "Hard-delete … Returns 404 if not found." |
| `POST "/action"` | Describe the bulk operation and what the response data contains |

```python
async def get_all(...):
    """Return a paginated list of users, optionally filtered by any combination of fields."""

async def update(...):
    """Partially update a user. Only fields present in the body are changed."""
```

---

## Rules

- Declare `GET /sub-path` routes **before** `GET /{id}` — FastAPI matches in order and will otherwise interpret the literal path as a UUID param.
- Always pass matching `status_code` to both the route decorator and `APIResponse`.
- Instantiate the service inside each handler, not at module level.
- Use `Query()` for each filter field individually — never `Depends(FilterRequest)` in GET endpoints.
- Use `Body(default=None)` for POST bulk-operation bodies so the endpoint accepts an empty body.
- Never call `uow.commit()` in a router — `uow_deps` handles it.
- Never import models directly into routers — use schemas and enums only.

# Service Rules

## Structure

Every service follows this layout:

```python
class XxxService(ActivityLogMixin):          # omit mixin if no audit logging
    _TABLE = XxxModel.__tablename__          # required by ActivityLogMixin
    _CACHE_PREFIX = _TABLE                   # omit if no caching

    def __init__(self, uow: UnitOfWork, ...) -> None: ...

    # 1. static cache-key helpers  (cache_get_by_id_key, cache_get_all_key, cache_invalidate)
    # 2. private fetch helper      (_fetch_xxx  — DB-only, used by mutations)
    # 3. read methods              (get_by_id, get_all)
    # 4. write methods             (create, update)
    # 5. delete methods            (delete, delete_all)
```

---

## Constructor

Always accept `UnitOfWork` and store it as `self._uow`. Never accept a repository directly.
When the service uses `ActivityLogMixin`, also accept `actor_id`, `company_id`, `ip_address`,
`user_agent` — all `| None = None` so existing callers don't break.

```python
def __init__(
    self,
    uow: UnitOfWork,
    actor_id: UUID | None = None,
    company_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    self._uow = uow
    self._actor_id = actor_id
    self._company_id = company_id
    self._ip_address = ip_address
    self._user_agent = user_agent
```

---

## ActivityLogMixin

Inherit `ActivityLogMixin` from `services/activity_log_service.py` to add audit logging.
Declare `_TABLE = XxxModel.__tablename__` as a class attribute — the mixin reads it when
building the log entry.

Call `_log_activity` inside write and delete methods **after** flush/refresh so the snapshot
reflects the committed state.

```python
from services.activity_log_service import ActivityLogMixin

class XxxService(ActivityLogMixin):
    _TABLE = XxxModel.__tablename__

    async def create(self, body: XxxCreateRequest) -> XxxModel:
        obj = await self._uow.xxx.create(...)
        await self._uow.flush()
        await self._uow.refresh(obj)
        after = XxxResponse.model_validate(obj).model_dump(mode="json")
        await self._log_activity(obj.id, ActivityLogAction.CREATE, after=after)
        return obj
```

| Action | `before` | `after` |
| --- | --- | --- |
| `CREATE` | `None` | serialized new record |
| `UPDATE` | serialized record before mutation | serialized record after refresh |
| `DELETE` | serialized record before deletion | `None` |

---

## Caching

### Cache key static methods

Declare one static method per lookup shape. Use `_CACHE_PREFIX` (set to `_TABLE`) as the
namespace so `cache_invalidate` can wipe all keys with a single pattern delete.

```python
_CACHE_PREFIX = XxxModel.__tablename__   # "xxx"

@staticmethod
def cache_get_by_id_key(obj_id: UUID) -> str:
    return f"{XxxService._CACHE_PREFIX}:id={obj_id}"

@staticmethod
def cache_get_all_key(page: int, limit: int, field_a: str | None, ...) -> str:
    return (
        f"{XxxService._CACHE_PREFIX}:list:page={page}:limit={limit}"
        f":field_a={field_a}:..."
    )
```

### `cache_invalidate`

Pattern-delete all keys for this resource. Call at the end of every mutation
(`create`, `update`, `delete`). Guard with `CACHE_ENABLED` — skip the Redis call entirely
when caching is off.

```python
@staticmethod
async def cache_invalidate() -> None:
    """Delete all user cache keys (items + lists)."""
    cfg = get_configs()
    if cfg.CACHE_ENABLED:
        await delete_cache_pattern(f"{XxxService._CACHE_PREFIX}:*")
```

### Private fetch helper

Mutations need a real ORM object (not a cached Pydantic model).
Add a private `_fetch_xxx` that always hits the DB and raises 404.
Use it in `update` and `delete` instead of the cached `get_by_id`.

```python
async def _fetch_xxx(self, id: UUID) -> XxxModel:
    """Fetch from DB and raise 404 if not found. Bypasses cache — use for mutations."""
    obj = await self._uow.xxx.get_by_id(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Xxx not found")
    return obj
```

### Read methods with cache

```python
async def get_by_id(self, id: UUID) -> XxxModel:
    cfg = get_configs()
    if cfg.CACHE_ENABLED:
        cached = await get_cache(self.cache_get_by_id_key(id))
        if cached is not None:
            return XxxResponse.model_validate_json(cached)  # type: ignore[return-value]

    obj = await self._fetch_xxx(id)

    if cfg.CACHE_ENABLED:
        await set_cache(
            self.cache_get_by_id_key(id),
            XxxResponse.model_validate(obj).model_dump_json(),
        )
    return obj
```

For list caching, serialize the full page as `{"items": [...], "total": n}` and store with
`set_cache`. On hit, deserialize with `json.loads` and `XxxResponse.model_validate` per item.

```python
async def get_all(self, filters, page=1, limit=10) -> Tuple[List[XxxModel], int]:
    cfg = get_configs()
    list_key = self.cache_get_all_key(page=page, limit=limit, ...)

    if cfg.CACHE_ENABLED:
        cached = await get_cache(list_key)
        if cached is not None:
            data = json.loads(cached)
            items = [XxxResponse.model_validate(i) for i in data["items"]]
            return items, data["total"]  # type: ignore[return-value]

    items, total = await self._uow.xxx.get_all(filters, page=page, limit=limit)

    if cfg.CACHE_ENABLED:
        payload = json.dumps({
            "items": [XxxResponse.model_validate(u).model_dump(mode="json") for u in items],
            "total": total,
        })
        await set_cache(list_key, payload)

    return items, total
```

### Mutations — invalidate after write

```python
async def create(self, body: XxxCreateRequest) -> XxxModel:
    obj = await self._uow.xxx.create(...)
    await self._uow.flush()
    await self._uow.refresh(obj)
    after = XxxResponse.model_validate(obj).model_dump(mode="json")
    await self._log_activity(obj.id, ActivityLogAction.CREATE, after=after)
    await self.cache_invalidate()   # wipes items + lists
    return obj

async def update(self, id: UUID, body: XxxUpdateRequest) -> XxxModel:
    obj = await self._fetch_xxx(id)            # bypass cache — need ORM object
    before = XxxResponse.model_validate(obj).model_dump(mode="json")
    await self._uow.xxx.update(obj, **body.model_dump(exclude_none=True))
    await self._uow.flush()
    await self._uow.refresh(obj)
    after = XxxResponse.model_validate(obj).model_dump(mode="json")
    await self._log_activity(id, ActivityLogAction.UPDATE, before=before, after=after)
    await self.cache_invalidate()
    return obj

async def delete(self, id: UUID) -> None:
    obj = await self._fetch_xxx(id)            # bypass cache — need ORM object
    before = XxxResponse.model_validate(obj).model_dump(mode="json")
    await self._uow.xxx.delete(obj)
    await self._log_activity(id, ActivityLogAction.DELETE, before=before)
    await self.cache_invalidate()
```

---

## Read methods

### `get_by_id`

Always raise `HTTPException(404)` when the record is not found — never return `None`.

```python
async def get_by_id(self, id: UUID) -> XxxModel:
    """Return a single record or raise 404."""
    obj = await self._uow.xxx.get_by_id(id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Xxx not found")
    return obj
```

### `get_all`

Pass through to the repository. Return `Tuple[List[XxxModel], int]`.

```python
async def get_all(
    self,
    filters: XxxFilterRequest,
    page: int = 1,
    limit: int = 10,
) -> Tuple[List[XxxModel], int]:
    """Return a paginated list and the total count."""
    return await self._uow.xxx.get_all(filters, page=page, limit=limit)
```

---

## Write methods

### `create`

After `create()`, call `flush()` then `refresh()` so the returned object has its
relations populated and its generated fields (id, timestamps) resolved.

```python
async def create(self, ...) -> XxxModel:
    """Create and return the record with all fields resolved."""
    obj = await self._uow.xxx.create(...)
    await self._uow.flush()
    await self._uow.refresh(obj)
    return obj
```

---

## Delete methods

### `delete`

Always fetch first via `get_by_id` (which raises 404 if missing), then delete.
Never accept a model object directly — keep the id-based interface consistent.

```python
async def delete(self, id: UUID) -> None:
    """Fetch then hard-delete. Raises 404 if not found."""
    obj = await self.get_by_id(id)
    await self._uow.xxx.delete(obj)
```

### `delete_all`

Pass through filters and return the deleted row count.

```python
async def delete_all(self, filters: XxxFilterRequest | None = None) -> int:
    """Bulk delete matching *filters*, or all rows if *filters* is None."""
    return await self._uow.xxx.delete_all(filters)
```

---

## Docstrings

Every public method gets a single-line docstring. State the non-obvious side-effect or guard.

| Method | What to document |
| --- | --- |
| `get_by_id` | "… or raise 404." |
| `get_by_<field>` | "… or raise 404." |
| `get_all` | "Return a paginated list … and the total count." |
| `create` | "… and return it with all fields resolved." (flush + refresh implied) |
| `update` | Which fields change and how (`exclude_none`) |
| `delete` | "Fetch … then hard-delete. Raises 404 if not found." |
| `delete_all` | That `filters=None` deletes everything; returns row count |

```python
async def update(self, id: UUID, body: XxxUpdateRequest) -> XxxModel:
    """Fetch by id, apply non-None fields from *body*, and return updated record."""

async def delete(self, id: UUID) -> None:
    """Fetch by id then hard-delete. Raises 404 if not found."""
```

---

## Rules

- Accept `UnitOfWork`, never a bare repository or `AsyncSession`.
- Never call `uow.commit()` — the `uow_deps` dependency commits on success automatically.
- `get_by_id` always raises `HTTPException(404)`, never returns `None`.
- After `create`, always call `flush()` + `refresh()` before returning the object.
- `delete` always goes through `_fetch_xxx` (DB bypass) so the ORM object is available for the audit snapshot and 404 is raised consistently.
- Use `| None` union syntax (Python 3.11+), not `Optional[X]`.
- Use `Tuple[List[XxxModel], int]` from `typing` for `get_all` return type.
- Cache: import `XxxResponse` for serialization only — not for response shaping. Document with a comment.
- Cache: mutations use `_fetch_xxx` (not cached `get_by_id`) to obtain a real ORM object.
- Cache: always call `cache_invalidate()` at the end of every mutation so list caches are also cleared.
- Cache: guard every Redis call with `if cfg.CACHE_ENABLED` — never assume Redis is available.
- Cache: `set_cache` TTL defaults to `CACHE_DEFAULT_TTL` from config — omit the `ttl` arg unless you need a custom value.
- ActivityLog: call `_log_activity` after `flush()` + `refresh()` so snapshots reflect the committed state.
- ActivityLog: `before`/`after` snapshots use `XxxResponse.model_validate(obj).model_dump(mode="json")` so UUIDs and datetimes are JSON-serializable.

# Repository Rules

## Structure

Every repository follows this layout:

```python
class XxxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # 1. private helpers  (_base_query, _apply_filters)
    # 2. read methods     (get_by_id, get_all, get_distinct_*)
    # 3. write methods    (create)
    # 4. delete methods   (delete, delete_all)
```

---

## Private helpers

### `_base_query`

Returns the base `select()` with all relationships required by the response schema
eagerly loaded via `selectinload`.

```python
def _base_query(self):
    """Base SELECT with <relations> eagerly loaded."""
    return select(XxxModel).options(
        selectinload(XxxModel.relation_a),
        selectinload(XxxModel.relation_b),
    )
```

### `_apply_filters`

Collects conditions into a list, then applies them in a single `.where(*conditions)`.
Works with both `select()` and `delete()` statements.

```python
def _apply_filters(self, stmt, filters: XxxFilterRequest):
    """Narrow *stmt* by every non-None field in *filters*."""
    conditions = []

    if filters.field is not None:
        conditions.append(XxxModel.field == filters.field)
    if filters.from_date is not None:
        conditions.append(XxxModel.created_at >= filters.from_date)
    if filters.to_date is not None:
        conditions.append(XxxModel.created_at <= filters.to_date)

    return stmt.where(*conditions)
```

---

## Read methods

### `get_by_id`

```python
async def get_by_id(self, id: uuid.UUID) -> XxxModel | None:
    """Return a single record by primary key, or None if not found."""
    stmt = self._base_query().where(XxxModel.id == id)
    result = await self._session.execute(stmt)
    return result.scalar_one_or_none()
```

### `get_all`

Returns `Tuple[List[XxxModel], int]` — items and total count in one call so
callers can build pagination metadata without a separate round-trip.
Use `page` + `limit`, not raw `offset`.

```python
async def get_all(
    self,
    filters: XxxFilterRequest,
    page: int = 1,
    limit: int = 10,
) -> Tuple[List[XxxModel], int]:
    """Return a page of records matching *filters* and the total count."""
    offset = (page - 1) * limit
    filter_stmt = self._apply_filters(self._base_query(), filters)

    count_stmt = self._apply_filters(
        select(func.count()).select_from(XxxModel), filters
    )
    total = (await self._session.execute(count_stmt)).scalar_one()

    stmt = (
        filter_stmt.order_by(XxxModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await self._session.execute(stmt)
    items = list(result.scalars().all())
    return (items, total)
```

> Always assign `list(result.scalars().all())` to `items` before returning — never inline it.
> Wrap the tuple return in parentheses: `return (items, total)` not `return items, total`.

---

## Write methods

### `create`

Stage the model with `session.add()`. **Do not commit or flush** — the service
layer owns the transaction.

```python
async def create(self, field_a: str, field_b: ...) -> XxxModel:
    """Stage a new record. Persisted on the next flush/commit."""
    obj = XxxModel(field_a=field_a, field_b=field_b)
    self._session.add(obj)
    return obj
```

---

## Delete methods

### `delete`

Delete a single already-loaded ORM object.

```python
async def delete(self, obj: XxxModel) -> None:
    """Hard-delete a single record."""
    await self._session.delete(obj)
```

### `delete_all`

Bulk DELETE via SQL — does **not** iterate objects.
`filters=None` deletes every row in the table.
Returns the number of deleted rows.

```python
async def delete_all(self, filters: XxxFilterRequest | None = None) -> int:
    """Hard-delete entries matching *filters*, or all entries if *filters* is None."""
    stmt = delete(XxxModel)
    if filters is not None:
        stmt = self._apply_filters(stmt, filters)
    result = cast(CursorResult, await self._session.execute(stmt))
    return result.rowcount
```

---

## Docstrings

Every public method gets a single-line docstring. Focus on the non-obvious behaviour, not the name.

| Method | What to document |
| --- | --- |
| `_base_query` | Which relations are eagerly loaded |
| `_apply_filters` | That it narrows by every non-None field |
| `get_by_id` | Returns `None` if not found (caller decides what to do) |
| `get_by_<field>` | Returns `None` if not found |
| `get_all` | That count is fetched in the same call |
| `create` | "Stage … Persisted on the next flush/commit." |
| `update` | That it mutates in place without `session.add()` |
| `delete` | "Hard-delete" to distinguish from soft-delete |
| `delete_all` | That `filters=None` deletes every row; returns row count |

```python
async def get_all(self, ...) -> Tuple[List[XxxModel], int]:
    """Return a page of records matching *filters* and the total count.

    The total count is fetched in the same call so callers can build
    pagination metadata without a separate round-trip.
    """
```

---

## Rules

- Use `selectinload` (not `joinedload`) to avoid row duplication on one-to-many relations.
- Name the multi-record read method `get_all`, never `list` (shadows the Python built-in).
- Use `page` + `limit` in `get_all`; compute `offset = (page - 1) * limit` internally.
- Import the filter request from `schemas/requests/`. Never import from `schemas/responses/`.
- Never call `session.commit()` or `session.flush()` inside a repository.
- Use `| None` union syntax (Python 3.11+), not `Optional[X]`, for return types.
- Use `Tuple[List[XxxModel], int]` from `typing` for `get_all` return type.
- Annotate `delete_all` result as `cast(CursorResult, ...)` — async session stubs type it as `Result` which lacks `rowcount`.
- Always assign `list(result.scalars().all())` to an `items` variable before returning — never inline it in the `return` statement.
- Wrap tuple returns in parentheses: `return (items, total)`, not `return items, total`.

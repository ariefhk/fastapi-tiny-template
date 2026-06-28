import uuid
from typing import List, Optional, Tuple, cast

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.activity_log_model import ActivityLogModel
from schemas.requests.activity_log_request import ActivityLogFilterRequest


class ActivityLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT with company and actor eagerly loaded."""
        return select(ActivityLogModel).options(
            selectinload(ActivityLogModel.company),
            selectinload(ActivityLogModel.actor),
        )

    def _apply_filters(self, stmt, filters: ActivityLogFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []

        if filters.company_id is not None:
            conditions.append(ActivityLogModel.company_id == filters.company_id)
        if filters.actor_id is not None:
            conditions.append(ActivityLogModel.actor_id == filters.actor_id)
        if filters.action is not None:
            conditions.append(ActivityLogModel.action == filters.action)
        if filters.table_name is not None:
            conditions.append(ActivityLogModel.table_name == filters.table_name)
        if filters.table_id is not None:
            conditions.append(ActivityLogModel.table_id == filters.table_id)
        if filters.from_date is not None:
            conditions.append(ActivityLogModel.created_at >= filters.from_date)
        if filters.to_date is not None:
            conditions.append(ActivityLogModel.created_at <= filters.to_date)

        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> ActivityLogModel | None:
        """Return a single activity log by primary key, or None if not found."""
        stmt = self._base_query().where(ActivityLogModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: ActivityLogFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[ActivityLogModel], int]:
        """Return a page of activity logs matching *filters* and the total count.

        The total count is fetched in the same call so callers can build
        pagination metadata without a separate round-trip.
        """
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)

        count_stmt = self._apply_filters(
            select(func.count()).select_from(ActivityLogModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            filter_stmt.order_by(ActivityLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

    async def create(
        self,
        company_id: Optional[uuid.UUID],
        table_name: str,
        table_id: Optional[uuid.UUID],
        action: str,
        actor_id: Optional[uuid.UUID],
        ip_address: Optional[str],
        user_agent: Optional[str],
        before: Optional[dict],
        after: Optional[dict],
    ) -> ActivityLogModel:
        """Stage a new audit entry. Persisted on the next flush/commit."""
        activity = ActivityLogModel(
            company_id=company_id,
            table_name=table_name,
            table_id=table_id,
            action=action,
            actor_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before=before,
            after=after,
        )
        self._session.add(activity)
        return activity

    async def get_distinct_table_names(self) -> List[str]:
        """Return sorted list of unique table names recorded in the audit log."""
        stmt = (
            select(ActivityLogModel.table_name)
            .distinct()
            .order_by(ActivityLogModel.table_name)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return items

    async def delete(self, activity: ActivityLogModel) -> None:
        """Hard-delete a single activity log entry."""
        await self._session.delete(activity)

    async def delete_all(self, filters: ActivityLogFilterRequest | None = None) -> int:
        """Hard-delete entries matching *filters*, or all entries if *filters* is None.

        Returns the number of deleted rows.
        """
        stmt = delete(ActivityLogModel)
        if filters is not None:
            stmt = self._apply_filters(stmt, filters)
        result = cast(CursorResult, await self._session.execute(stmt))
        return result.rowcount

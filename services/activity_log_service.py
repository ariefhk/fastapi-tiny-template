from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException

from databases.unit_of_work import UnitOfWork
from models.activity_log_model import ActivityLogAction, ActivityLogModel
from schemas.requests.activity_log_request import ActivityLogFilterRequest


class ActivityLogMixin:
    """Mixin that adds `_log_activity` to any service that declares _TABLE and _uow."""

    _TABLE: str
    _uow: UnitOfWork

    async def _log_activity(
        self,
        table_id: UUID,
        action: ActivityLogAction,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
    ) -> None:
        await self._uow.activity_logs.create(
            company_id=getattr(self, "_company_id", None),
            actor_id=getattr(self, "_actor_id", None),
            table_name=self._TABLE,
            table_id=table_id,
            action=action,
            before=before,
            after=after,
            ip_address=getattr(self, "_ip_address", None),
            user_agent=getattr(self, "_user_agent", None),
        )


class ActivityLogService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get_by_id(self, id: UUID) -> ActivityLogModel:
        """Return a single activity log or raise 404."""
        activity = await self._uow.activity_logs.get_by_id(id)
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity log not found")
        return activity

    async def get_all(
        self,
        filters: ActivityLogFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[ActivityLogModel], int]:
        """Return a paginated list of activity logs and the total count."""
        return await self._uow.activity_logs.get_all(filters, page=page, limit=limit)

    async def create(
        self,
        company_id: Optional[UUID],
        table_name: str,
        table_id: Optional[UUID],
        action: ActivityLogAction,
        actor_id: Optional[UUID],
        ip_address: Optional[str],
        user_agent: Optional[str],
        before: Optional[dict] = None,
        after: Optional[dict] = None,
    ) -> ActivityLogModel:
        """Create an audit log entry and flush so it can be returned with relations."""
        activity = await self._uow.activity_logs.create(
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
        await self._uow.flush()
        await self._uow.refresh(activity)
        return activity

    async def get_distinct_table_names(self) -> List[str]:
        """Return sorted unique table names present in the audit log."""
        return await self._uow.activity_logs.get_distinct_table_names()

    async def delete(self, id: UUID) -> None:
        """Fetch by id then hard-delete the entry. Raises 404 if not found."""
        activity = await self.get_by_id(id)
        await self._uow.activity_logs.delete(activity)

    async def delete_all(self, filters: ActivityLogFilterRequest | None = None) -> int:
        """Hard-delete entries matching *filters*, or all entries if *filters* is None.

        Returns the number of deleted rows.
        """
        return await self._uow.activity_logs.delete_all(filters)

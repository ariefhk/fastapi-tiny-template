import uuid
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feature_model import FeatureModel
from schemas.requests.feature_request import FeatureFilterRequest


class FeatureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        """Base SELECT for features."""
        return select(FeatureModel)

    def _apply_filters(self, stmt, filters: FeatureFilterRequest):
        """Narrow *stmt* by every non-None field in *filters*."""
        conditions = []
        if filters.key is not None:
            conditions.append(FeatureModel.key.ilike(f"%{filters.key}%"))
        if filters.name is not None:
            conditions.append(FeatureModel.name.ilike(f"%{filters.name}%"))
        if filters.kind is not None:
            conditions.append(FeatureModel.kind == filters.kind)
        return stmt.where(*conditions)

    async def get_by_id(self, id: uuid.UUID) -> FeatureModel | None:
        """Return a single feature by primary key, or None if not found."""
        stmt = self._base_query().where(FeatureModel.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> FeatureModel | None:
        """Return a single feature by unique key, or None if not found."""
        stmt = self._base_query().where(FeatureModel.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        filters: FeatureFilterRequest,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[FeatureModel], int]:
        """Return a page of features matching *filters* and the total count."""
        offset = (page - 1) * limit
        filter_stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = self._apply_filters(
            select(func.count()).select_from(FeatureModel), filters
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            filter_stmt.order_by(FeatureModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return (items, total)

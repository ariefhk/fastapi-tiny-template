import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.plan_model import PlanIntervalEnum, PlanModel


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(PlanModel)

    async def get_all(self, offset: int, limit: int) -> Tuple[List[PlanModel], int]:
        count_stmt = select(func.count()).select_from(PlanModel)
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = self._base_query().order_by(PlanModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return (list(result.scalars().all()), total)

    async def get_by_id(self, plan_id: uuid.UUID) -> Optional[PlanModel]:
        stmt = self._base_query().where(PlanModel.id == plan_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[PlanModel]:
        stmt = self._base_query().where(PlanModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        slug: str,
        price_cents: int = 0,
        currency: str = "usd",
        interval: PlanIntervalEnum = PlanIntervalEnum.MONTH,
        is_active: bool = True,
    ) -> PlanModel:
        plan = PlanModel(
            name=name,
            slug=slug,
            price_cents=price_cents,
            currency=currency,
            interval=interval,
            is_active=is_active,
        )
        self._session.add(plan)
        return plan

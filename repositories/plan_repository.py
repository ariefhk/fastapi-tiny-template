from sqlalchemy.ext.asyncio import AsyncSession

from models.plan_model import PlanIntervalEnum, PlanModel


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

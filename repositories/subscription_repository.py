import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription_model import SubscriptionModel


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(SubscriptionModel)

    async def get_by_company(
        self, company_id: uuid.UUID
    ) -> Optional[SubscriptionModel]:
        stmt = self._base_query().where(SubscriptionModel.company_id == company_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        company_id: uuid.UUID,
    ) -> SubscriptionModel:
        subscription = SubscriptionModel(
            company_id=company_id,
        )
        self._session.add(subscription)
        return subscription

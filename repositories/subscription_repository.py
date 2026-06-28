import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription_model import SubscriptionModel


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        company_id: uuid.UUID,
    ) -> SubscriptionModel:
        subscription = SubscriptionModel(
            company_id=company_id,
        )
        self._session.add(subscription)
        return subscription

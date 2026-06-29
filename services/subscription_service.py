import uuid

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from schemas.responses.subscription_response import SubscriptionResponse


class SubscriptionService:
    def __init__(self, uow: UnitOfWork, company_id: uuid.UUID) -> None:
        self._uow = uow
        self._company_id = company_id

    async def get_by_company(self) -> SubscriptionResponse:
        subscription = await self._uow.subscriptions.get_by_company(self._company_id)
        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found"
            )
        return SubscriptionResponse.model_validate(subscription)

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.plan_feature_model import PlanFeatureModel


class PlanFeatureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        plan_id: uuid.UUID,
        feature_id: uuid.UUID,
        enabled: bool = True,
        limit_value: Optional[int] = None,
    ) -> PlanFeatureModel:
        plan_feature = PlanFeatureModel(
            plan_id=plan_id,
            feature_id=feature_id,
            enabled=enabled,
            limit_value=limit_value,
        )
        self._session.add(plan_feature)
        return plan_feature

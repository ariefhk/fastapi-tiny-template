import uuid
from typing import List, Tuple

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from schemas.responses.plan_response import PlanResponse


class PlanService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get_all(self, page: int = 1, limit: int = 50) -> Tuple[List[PlanResponse], int]:
        offset = (page - 1) * limit
        result = await self._uow.plans.get_all(offset, limit)
        plans = result[0]
        total = result[1]

        response_list: List[PlanResponse] = []
        for plan in plans:
            response_list.append(PlanResponse.model_validate(plan))

        return response_list, total

    async def get_one(self, plan_id: uuid.UUID) -> PlanResponse:
        plan = await self._uow.plans.get_by_id(plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return PlanResponse.model_validate(plan)

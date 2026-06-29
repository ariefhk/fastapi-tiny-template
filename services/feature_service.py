import uuid
from typing import List, Tuple

from fastapi import HTTPException, status

from databases.unit_of_work import UnitOfWork
from schemas.requests.feature_request import FeatureFilterRequest
from schemas.responses.feature_response import FeatureResponse


class FeatureService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get_all(self, page: int = 1, limit: int = 50) -> Tuple[List[FeatureResponse], int]:
        features, total = await self._uow.features.get_all(
            FeatureFilterRequest(), page=page, limit=limit
        )
        return [FeatureResponse.model_validate(f) for f in features], total

    async def get_one(self, feature_id: uuid.UUID) -> FeatureResponse:
        feature = await self._uow.features.get_by_id(feature_id)
        if feature is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")
        return FeatureResponse.model_validate(feature)

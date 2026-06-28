import uuid

from pydantic import BaseModel


class PlanFeatureCreateRequest(BaseModel):
    plan_id: uuid.UUID
    feature_id: uuid.UUID
    enabled: bool = True
    limit_value: int | None = None


class PlanFeatureUpdateRequest(BaseModel):
    enabled: bool | None = None
    limit_value: int | None = None

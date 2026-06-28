import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlanFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    feature_id: uuid.UUID
    enabled: bool
    limit_value: int | None
    created_at: datetime
    updated_at: datetime

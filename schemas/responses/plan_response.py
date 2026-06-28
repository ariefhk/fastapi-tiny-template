import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.plan_model import PlanIntervalEnum


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    price_cents: int
    currency: str
    interval: PlanIntervalEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime

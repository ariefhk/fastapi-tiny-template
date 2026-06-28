from pydantic import BaseModel

from models.plan_model import PlanIntervalEnum


class PlanCreateRequest(BaseModel):
    name: str
    slug: str
    price_cents: int = 0
    currency: str = "usd"
    interval: PlanIntervalEnum = PlanIntervalEnum.MONTH
    is_active: bool = True


class PlanUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    price_cents: int | None = None
    currency: str | None = None
    interval: PlanIntervalEnum | None = None
    is_active: bool | None = None

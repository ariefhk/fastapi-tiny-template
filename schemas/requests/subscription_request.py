import uuid

from pydantic import BaseModel


class SubscriptionCreateRequest(BaseModel):
    company_id: uuid.UUID


class SubscriptionUpdateRequest(BaseModel):
    company_id: uuid.UUID | None = None

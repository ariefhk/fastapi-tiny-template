import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    external_event_id: str
    type: str
    payload: dict | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

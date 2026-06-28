import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.activity_log_model import ActivityLogAction


class ActivityActorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str


class ActivityCompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: ActivityCompanyResponse | None
    actor: ActivityActorResponse | None
    action: ActivityLogAction
    table_name: str
    table_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    updated_at: datetime

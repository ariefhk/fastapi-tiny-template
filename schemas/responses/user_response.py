import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    mfa_enabled: bool
    email_verified_at: datetime | None
    last_active_company_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

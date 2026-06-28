import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    active_company_id: uuid.UUID
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

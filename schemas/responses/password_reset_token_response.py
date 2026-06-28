import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PasswordResetTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
    updated_at: datetime

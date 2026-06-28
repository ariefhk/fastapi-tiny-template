import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    resource: str
    action: str
    description: str | None
    created_at: datetime
    updated_at: datetime

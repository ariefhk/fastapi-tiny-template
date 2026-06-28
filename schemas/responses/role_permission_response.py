import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RolePermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role_id: uuid.UUID
    permission_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

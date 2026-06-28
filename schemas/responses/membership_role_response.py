import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MembershipRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    membership_id: uuid.UUID
    role_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

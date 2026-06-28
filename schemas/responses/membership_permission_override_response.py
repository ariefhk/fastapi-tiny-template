import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.membership_permission_override_model import OverrideEffectEnum


class MembershipPermissionOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    membership_id: uuid.UUID
    permission_id: uuid.UUID
    effect: OverrideEffectEnum
    created_at: datetime
    updated_at: datetime

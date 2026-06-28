import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.membership_model import MembershipStatusEnum


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    status: MembershipStatusEnum
    created_at: datetime
    updated_at: datetime

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.invitation_model import InvitationStatusEnum


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    role_id: uuid.UUID | None
    invited_by_user_id: uuid.UUID | None
    status: InvitationStatusEnum
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

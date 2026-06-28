import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from models.invitation_model import InvitationStatusEnum


class InvitationCreateRequest(BaseModel):
    company_id: uuid.UUID
    email: EmailStr
    role_id: uuid.UUID | None = None
    invited_by_user_id: uuid.UUID | None = None
    expires_at: datetime


class InvitationUpdateRequest(BaseModel):
    status: InvitationStatusEnum | None = None
    role_id: uuid.UUID | None = None

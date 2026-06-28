import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.auth_identity_model import AuthProviderEnum


class AuthIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: AuthProviderEnum
    provider_user_id: str | None
    email: str | None
    created_at: datetime
    updated_at: datetime

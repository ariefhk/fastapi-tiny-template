import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    user_id: uuid.UUID
    active_company_id: uuid.UUID
    refresh_token_hash: str
    expires_at: datetime


class SessionFilterRequest(BaseModel):
    user_id: uuid.UUID | None = None
    active_company_id: uuid.UUID | None = None

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    owner_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

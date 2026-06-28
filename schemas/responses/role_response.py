import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

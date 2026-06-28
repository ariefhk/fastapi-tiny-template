import uuid
from datetime import datetime

from pydantic import BaseModel

from models.activity_log_model import ActivityLogAction


class ActivityLogFilterRequest(BaseModel):
    company_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: ActivityLogAction | None = None
    table_name: str | None = None
    table_id: uuid.UUID | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None


class ActivityLogSearchRequest(ActivityLogFilterRequest):
    page: int = 1
    limit: int = 10

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from models.membership_model import MembershipStatusEnum


class MemberResponse(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: Optional[str]
    status: MembershipStatusEnum
    role_ids: List[uuid.UUID]
    joined_at: datetime

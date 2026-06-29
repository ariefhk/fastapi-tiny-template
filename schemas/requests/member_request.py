import uuid
from typing import List

from pydantic import BaseModel

from models.membership_permission_override_model import OverrideEffectEnum


class MemberRoleAssignment(BaseModel):
    role_ids: List[uuid.UUID]


class MemberOverrideCreate(BaseModel):
    permission_key: str
    effect: OverrideEffectEnum

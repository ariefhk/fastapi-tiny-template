import uuid

from pydantic import BaseModel


class MembershipRoleCreateRequest(BaseModel):
    membership_id: uuid.UUID
    role_id: uuid.UUID


class MembershipRoleFilterRequest(BaseModel):
    membership_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None

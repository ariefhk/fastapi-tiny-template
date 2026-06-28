import uuid

from pydantic import BaseModel

from models.membership_model import MembershipStatusEnum


class MembershipCreateRequest(BaseModel):
    user_id: uuid.UUID
    company_id: uuid.UUID
    status: MembershipStatusEnum = MembershipStatusEnum.ACTIVE


class MembershipUpdateRequest(BaseModel):
    status: MembershipStatusEnum | None = None


class MembershipFilterRequest(BaseModel):
    user_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    status: MembershipStatusEnum | None = None

import uuid

from pydantic import BaseModel

from models.membership_permission_override_model import OverrideEffectEnum


class MembershipPermissionOverrideCreateRequest(BaseModel):
    membership_id: uuid.UUID
    permission_id: uuid.UUID
    effect: OverrideEffectEnum


class MembershipPermissionOverrideUpdateRequest(BaseModel):
    effect: OverrideEffectEnum | None = None


class MembershipPermissionOverrideFilterRequest(BaseModel):
    membership_id: uuid.UUID | None = None
    permission_id: uuid.UUID | None = None
    effect: OverrideEffectEnum | None = None

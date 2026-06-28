import uuid

from pydantic import BaseModel


class RolePermissionCreateRequest(BaseModel):
    role_id: uuid.UUID
    permission_id: uuid.UUID


class RolePermissionFilterRequest(BaseModel):
    role_id: uuid.UUID | None = None
    permission_id: uuid.UUID | None = None

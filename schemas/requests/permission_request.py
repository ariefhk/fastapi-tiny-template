from pydantic import BaseModel


class PermissionCreateRequest(BaseModel):
    key: str
    resource: str
    action: str
    description: str | None = None


class PermissionUpdateRequest(BaseModel):
    key: str | None = None
    resource: str | None = None
    action: str | None = None
    description: str | None = None


class PermissionFilterRequest(BaseModel):
    key: str | None = None
    resource: str | None = None
    action: str | None = None

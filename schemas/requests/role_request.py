import uuid

from pydantic import BaseModel


class RoleCreateRequest(BaseModel):
    company_id: uuid.UUID | None = None
    name: str
    slug: str
    is_system: bool = False


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None


class RoleFilterRequest(BaseModel):
    company_id: uuid.UUID | None = None
    name: str | None = None
    slug: str | None = None
    is_system: bool | None = None

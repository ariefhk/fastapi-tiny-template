import uuid

from pydantic import BaseModel


class CompanyCreateRequest(BaseModel):
    name: str
    slug: str
    owner_user_id: uuid.UUID | None = None


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None


class CompanyFilterRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    owner_user_id: uuid.UUID | None = None

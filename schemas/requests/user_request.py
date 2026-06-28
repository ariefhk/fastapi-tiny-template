import uuid

from pydantic import BaseModel, EmailStr


class UserFilterRequest(BaseModel):
    email: str | None = None
    name: str | None = None
    mfa_enabled: bool | None = None
    email_verified: bool | None = None
    last_active_company_id: uuid.UUID | None = None


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    mfa_enabled: bool = False


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    mfa_enabled: bool | None = None
    last_active_company_id: uuid.UUID | None = None

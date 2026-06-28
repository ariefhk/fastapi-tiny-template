from pydantic import BaseModel, EmailStr

from models.auth_identity_model import AuthProviderEnum


class AuthIdentityCreateRequest(BaseModel):
    provider: AuthProviderEnum
    provider_user_id: str | None = None
    password_hash: str | None = None
    email: EmailStr | None = None


class AuthIdentityUpdateRequest(BaseModel):
    provider_user_id: str | None = None
    password_hash: str | None = None
    email: EmailStr | None = None

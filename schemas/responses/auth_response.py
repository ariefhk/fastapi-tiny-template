import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from schemas.responses.user_response import UserResponse


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class TokenResponse(BaseModel):
    """Returned on register and login — includes both tokens and the authenticated user."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    """Returned on token refresh — access token only."""

    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: Optional[str]
    company_id: uuid.UUID
    plan: Optional[str]
    permissions: List[str]
    features: Dict[str, Any]
    companies: List[CompanyBrief]

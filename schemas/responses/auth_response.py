from pydantic import BaseModel

from schemas.responses.user_response import UserResponse


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

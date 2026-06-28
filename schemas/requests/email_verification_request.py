from pydantic import BaseModel


class EmailVerificationCreateRequest(BaseModel):
    token: str


class EmailVerificationVerifyRequest(BaseModel):
    token: str

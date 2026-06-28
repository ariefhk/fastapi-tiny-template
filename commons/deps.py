from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from commons.security import decode_access_token
from databases.unit_of_work import UnitOfWork, uow_deps
from models.session_model import SessionModel
from models.user_model import UserModel

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentAuth:
    user: UserModel
    session: SessionModel


async def get_current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    uow: UnitOfWork = Depends(uow_deps),
) -> CurrentAuth:
    """FastAPI dependency: decode JWT, validate session still exists, return user + session."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    session_id = UUID(payload["sid"])
    user_id = UUID(payload["sub"])

    session = await uow.sessions.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Session revoked")

    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return CurrentAuth(user=user, session=session)

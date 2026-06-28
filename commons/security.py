import datetime as dt
import hashlib
import secrets
import uuid
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from commons.config import get_configs


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    active_company_id: Optional[uuid.UUID] = None,
) -> str:
    cfg = get_configs()
    now = dt.datetime.now(dt.timezone.utc)
    expire = now + dt.timedelta(minutes=cfg.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "active_company_id": str(active_company_id) if active_company_id else None,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, cfg.JWT_SECRET_KEY, algorithm=cfg.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Return the decoded payload dict, or None if the token is invalid/expired."""
    cfg = get_configs()
    try:
        payload = jwt.decode(token, cfg.JWT_SECRET_KEY, algorithms=[cfg.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except (JWTError, ValueError):
        return None


def generate_refresh_token() -> str:
    """Return a URL-safe random token string (not a JWT)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of the raw refresh token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> dt.datetime:
    cfg = get_configs()
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        days=cfg.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

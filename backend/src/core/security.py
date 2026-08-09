import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status

from src.core.config import Settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(
    *, sub: str, email: str, department: str, is_admin: bool, settings: Settings
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "department": department,
        "is_admin": is_admin,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    return {
        "sub": payload["sub"],
        "email": payload["email"],
        "department": payload["department"],
        "is_admin": payload["is_admin"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Deliberately not `settings: Settings = Depends(Settings)` — combining a
    # Depends()-injected BaseSettings model with a route that also has a
    # Pydantic request body breaks FastAPI's body-model generation (it tries
    # to introspect Settings' pydantic-settings-specific init kwargs, e.g.
    # `_env_file`, and rejects the leading underscore). Every other endpoint
    # in this codebase already calls Settings() directly for the same
    # reason; this just brings get_current_user in line with that. Also
    # constructed only after the header check above, so a request with no
    # Authorization header never needs env vars/.env to be configured at all
    # (caught in CI: no backend/.env there, unlike local dev).
    settings = Settings()

    token = authorization.removeprefix("Bearer ")
    try:
        return decode_access_token(token, settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

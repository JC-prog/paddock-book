from datetime import datetime, timedelta, timezone

from src.core.config import Settings
from src.core import security as security_module
from src.modules.auth import repository as repository_module

_GENERIC_LOGIN_ERROR = "Invalid email or password"
_GENERIC_REFRESH_ERROR = "Invalid or expired refresh token"
_EMPTY_PASSWORD_ERROR = "Password must not be empty"
_DUPLICATE_EMAIL_ERROR = "An account with this email already exists"


def _issue_session(user: dict, *, conn, repository, security, settings) -> dict:
    access_token = security.create_access_token(
        sub=str(user["id"]), email=user["email"], department=user["department"], settings=settings
    )

    refresh_token_raw = security.generate_refresh_token()
    refresh_token_hash = security.hash_token(refresh_token_raw)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    repository.create_refresh_token(conn, user["id"], refresh_token_hash, expires_at)
    conn.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_raw,
        "refresh_token_expires_at": expires_at,
        "user": {"id": str(user["id"]), "email": user["email"], "department": user["department"]},
    }


def login(
    email: str,
    password: str,
    *,
    conn,
    repository=repository_module,
    security=security_module,
    settings_factory=Settings,
) -> dict:
    settings = settings_factory()
    user = repository.get_user_by_email(conn, email)

    if user is None or not security.verify_password(password, user["password_hash"]):
        raise ValueError(_GENERIC_LOGIN_ERROR)

    return _issue_session(user, conn=conn, repository=repository, security=security, settings=settings)


def refresh_access_token(
    refresh_token_raw: str,
    *,
    conn,
    repository=repository_module,
    security=security_module,
    settings_factory=Settings,
) -> dict:
    settings = settings_factory()
    token_hash = security.hash_token(refresh_token_raw)
    existing = repository.get_valid_refresh_token(conn, token_hash)

    if existing is None:
        raise ValueError(_GENERIC_REFRESH_ERROR)

    user = repository.get_user_by_id(conn, existing["user_id"])
    repository.revoke_refresh_token(conn, token_hash)

    return _issue_session(user, conn=conn, repository=repository, security=security, settings=settings)


def logout(
    refresh_token_raw: str | None,
    *,
    conn,
    repository=repository_module,
    security=security_module,
) -> None:
    if refresh_token_raw is None:
        return

    token_hash = security.hash_token(refresh_token_raw)
    repository.revoke_refresh_token(conn, token_hash)
    conn.commit()


def register(
    email: str,
    password: str,
    department: str,
    *,
    conn,
    repository=repository_module,
    security=security_module,
    settings_factory=Settings,
) -> dict:
    if not password:
        raise ValueError(_EMPTY_PASSWORD_ERROR)

    if repository.get_user_by_email(conn, email) is not None:
        raise ValueError(_DUPLICATE_EMAIL_ERROR)

    settings = settings_factory()
    password_hash = security.hash_password(password)
    user = repository.create_user(conn, email, password_hash, department)

    return _issue_session(user, conn=conn, repository=repository, security=security, settings=settings)

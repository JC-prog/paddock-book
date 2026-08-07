from fastapi import APIRouter, Cookie, HTTPException, Response, status

from src.core.config import Settings
from src.core.db import get_connection
from src.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from src.modules.auth.service import login as login_service
from src.modules.auth.service import logout as logout_service
from src.modules.auth.service import refresh_access_token as refresh_service
from src.modules.auth.service import register as register_service

router = APIRouter(prefix="/v1/auth")

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/v1/auth"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    settings = Settings()
    conn = get_connection()
    try:
        result = login_service(payload.email, payload.password, conn=conn, settings_factory=lambda: settings)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    finally:
        conn.close()

    _set_refresh_cookie(response, result["refresh_token"], settings)
    return AuthResponse(access_token=result["access_token"], user=UserPublic(**result["user"]))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response) -> AuthResponse:
    settings = Settings()
    conn = get_connection()
    try:
        result = register_service(
            payload.email, payload.password, payload.department, conn=conn, settings_factory=lambda: settings
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    finally:
        conn.close()

    _set_refresh_cookie(response, result["refresh_token"], settings)
    return AuthResponse(access_token=result["access_token"], user=UserPublic(**result["user"]))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, refresh_token: str | None = Cookie(default=None)) -> None:
    conn = get_connection()
    try:
        logout_service(refresh_token, conn=conn)
    finally:
        conn.close()

    _clear_refresh_cookie(response)


@router.post("/refresh", response_model=AuthResponse)
def refresh(response: Response, refresh_token: str | None = Cookie(default=None)) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    settings = Settings()
    conn = get_connection()
    try:
        result = refresh_service(refresh_token, conn=conn, settings_factory=lambda: settings)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    finally:
        conn.close()

    _set_refresh_cookie(response, result["refresh_token"], settings)
    return AuthResponse(access_token=result["access_token"], user=UserPublic(**result["user"]))

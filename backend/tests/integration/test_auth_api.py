import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from src.core import security
from src.main import app
from src.modules.auth import repository


def _connect() -> psycopg.Connection:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://paddockbook:paddockbook@localhost:5432/paddockbook",
    )
    return psycopg.connect(dsn)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _unique_email() -> str:
    return f"api-test-{uuid.uuid4()}@example.com"


def _seed_user(email: str, password: str, department: str = "sporting") -> dict:
    with _connect() as conn:
        user = repository.create_user(conn, email, security.hash_password(password), department)
        conn.commit()
    return user


def _cleanup(email: str) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM refresh_tokens WHERE user_id = "
                "(SELECT id FROM users WHERE email = %s)",
                (email,),
            )
            cur.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()


def test_login_returns_200_with_access_token_and_refresh_cookie(client):
    email = _unique_email()
    _seed_user(email, "correct-password")

    try:
        response = client.post(
            "/v1/auth/login", json={"email": email, "password": "correct-password"}
        )

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["user"]["email"] == email
        assert "refresh_token" in response.cookies
    finally:
        _cleanup(email)


def test_login_returns_401_for_wrong_password(client):
    email = _unique_email()
    _seed_user(email, "correct-password")

    try:
        response = client.post(
            "/v1/auth/login", json={"email": email, "password": "wrong-password"}
        )

        assert response.status_code == 401
    finally:
        _cleanup(email)


def test_login_returns_401_for_unknown_email(client):
    response = client.post(
        "/v1/auth/login", json={"email": _unique_email(), "password": "whatever"}
    )

    assert response.status_code == 401


def test_login_error_does_not_reveal_whether_email_exists(client):
    email = _unique_email()
    _seed_user(email, "correct-password")

    try:
        wrong_password_response = client.post(
            "/v1/auth/login", json={"email": email, "password": "wrong-password"}
        )
        unknown_email_response = client.post(
            "/v1/auth/login", json={"email": _unique_email(), "password": "whatever"}
        )

        assert wrong_password_response.status_code == unknown_email_response.status_code
        assert wrong_password_response.json() == unknown_email_response.json()
    finally:
        _cleanup(email)


def test_refresh_returns_new_access_token_and_rotates_cookie(client):
    email = _unique_email()
    _seed_user(email, "correct-password")

    try:
        login_response = client.post(
            "/v1/auth/login", json={"email": email, "password": "correct-password"}
        )
        old_refresh_cookie = login_response.cookies.get("refresh_token")

        refresh_response = client.post("/v1/auth/refresh")

        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()
        new_refresh_cookie = refresh_response.cookies.get("refresh_token")
        assert new_refresh_cookie is not None
        assert new_refresh_cookie != old_refresh_cookie
    finally:
        _cleanup(email)


def test_refresh_returns_401_without_a_valid_cookie(client):
    response = client.post("/v1/auth/refresh")

    assert response.status_code == 401


def test_refresh_returns_401_after_the_old_token_was_already_rotated(client):
    email = _unique_email()
    _seed_user(email, "correct-password")

    try:
        login_response = client.post(
            "/v1/auth/login", json={"email": email, "password": "correct-password"}
        )
        original_refresh_cookie = login_response.cookies.get("refresh_token")

        client.post("/v1/auth/refresh")  # rotates — the original cookie is now revoked

        # Simulate reusing the now-stale original cookie instead of the rotated one.
        client.cookies.set("refresh_token", original_refresh_cookie)
        response = client.post("/v1/auth/refresh")

        assert response.status_code == 401
    finally:
        _cleanup(email)

import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from src.modules.auth.repository import (
    create_refresh_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_valid_refresh_token,
    revoke_refresh_token,
)


def _connect() -> psycopg.Connection:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://paddockbook:paddockbook@localhost:5432/paddockbook",
    )
    return psycopg.connect(dsn)


@pytest.fixture
def conn():
    connection = _connect()
    yield connection
    connection.rollback()
    connection.close()


def _unique_email() -> str:
    return f"repo-test-{uuid.uuid4()}@example.com"


def _cleanup(email: str) -> None:
    with _connect() as cleanup_conn:
        with cleanup_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM refresh_tokens WHERE user_id = "
                "(SELECT id FROM users WHERE email = %s)",
                (email,),
            )
            cur.execute("DELETE FROM users WHERE email = %s", (email,))
        cleanup_conn.commit()


def test_create_user_and_get_by_email_round_trip(conn):
    email = _unique_email()

    created = create_user(conn, email, "hashed-password", "sporting")
    conn.commit()

    try:
        assert created["email"] == email
        assert created["department"] == "sporting"

        fetched = get_user_by_email(conn, email)
        assert fetched["id"] == created["id"]
        assert fetched["email"] == email
        assert fetched["password_hash"] == "hashed-password"
        assert fetched["department"] == "sporting"
    finally:
        _cleanup(email)


def test_get_user_by_email_returns_none_for_unknown_email(conn):
    assert get_user_by_email(conn, _unique_email()) is None


def test_create_user_rejects_duplicate_email(conn):
    email = _unique_email()
    create_user(conn, email, "hashed-password", "sporting")
    conn.commit()

    try:
        with pytest.raises(psycopg.errors.UniqueViolation):
            create_user(conn, email, "another-hash", "technical")
        conn.rollback()
    finally:
        _cleanup(email)


def test_create_refresh_token_and_get_valid_refresh_token_round_trip(conn):
    email = _unique_email()
    user = create_user(conn, email, "hashed-password", "sporting")
    conn.commit()

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        created = create_refresh_token(conn, user["id"], "a-token-hash", expires_at)
        conn.commit()

        fetched = get_valid_refresh_token(conn, "a-token-hash")
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["user_id"] == user["id"]
    finally:
        _cleanup(email)


def test_get_valid_refresh_token_returns_none_for_unknown_hash(conn):
    assert get_valid_refresh_token(conn, "no-such-token-hash") is None


def test_get_valid_refresh_token_excludes_revoked_token(conn):
    email = _unique_email()
    user = create_user(conn, email, "hashed-password", "sporting")
    conn.commit()

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        create_refresh_token(conn, user["id"], "revoked-token-hash", expires_at)
        conn.commit()

        revoke_refresh_token(conn, "revoked-token-hash")
        conn.commit()

        assert get_valid_refresh_token(conn, "revoked-token-hash") is None
    finally:
        _cleanup(email)


def test_get_valid_refresh_token_excludes_expired_token(conn):
    email = _unique_email()
    user = create_user(conn, email, "hashed-password", "sporting")
    conn.commit()

    try:
        already_expired = datetime.now(timezone.utc) - timedelta(minutes=1)
        create_refresh_token(conn, user["id"], "expired-token-hash", already_expired)
        conn.commit()

        assert get_valid_refresh_token(conn, "expired-token-hash") is None
    finally:
        _cleanup(email)


def test_revoke_refresh_token_is_a_no_op_for_unknown_hash(conn):
    revoke_refresh_token(conn, "no-such-token-hash")
    conn.commit()


def test_get_user_by_id_returns_the_matching_user(conn):
    email = _unique_email()
    created = create_user(conn, email, "hashed-password", "financial")
    conn.commit()

    try:
        fetched = get_user_by_id(conn, created["id"])
        assert fetched is not None
        assert fetched["email"] == email
        assert fetched["department"] == "financial"
    finally:
        _cleanup(email)


def test_get_user_by_id_returns_none_for_unknown_id(conn):
    assert get_user_by_id(conn, "00000000-0000-0000-0000-000000000000") is None

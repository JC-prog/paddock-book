import os
import uuid

import psycopg
import pytest

from src.modules.admin.repository import (
    get_log_destination_setting,
    promote_to_admin,
    set_log_destination_setting,
)
from src.modules.auth.repository import create_user


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
    return f"promote-test-{uuid.uuid4()}@example.com"


def test_get_log_destination_setting_returns_none_when_no_row_exists(conn):
    assert get_log_destination_setting(conn) is None


def test_set_log_destination_setting_creates_the_row_on_first_call(conn):
    set_log_destination_setting(conn, False)

    assert get_log_destination_setting(conn) is False


def test_set_log_destination_setting_updates_an_existing_row(conn):
    set_log_destination_setting(conn, True)
    set_log_destination_setting(conn, False)

    assert get_log_destination_setting(conn) is False


def test_promote_to_admin_sets_is_admin_true_for_an_existing_account(conn):
    email = _unique_email()
    user = create_user(conn, email, "not-a-real-hash", "sporting")

    result = promote_to_admin(conn, email)

    assert result == {"id": user["id"], "email": email}
    with conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user["id"],))
        assert cur.fetchone()[0] is True


def test_promote_to_admin_returns_none_for_an_unknown_email(conn):
    assert promote_to_admin(conn, "nobody-at-all@example.com") is None


def test_promote_to_admin_is_idempotent_for_an_already_admin_account(conn):
    email = _unique_email()
    user = create_user(conn, email, "not-a-real-hash", "sporting")
    promote_to_admin(conn, email)

    result = promote_to_admin(conn, email)

    assert result == {"id": user["id"], "email": email}
    with conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user["id"],))
        assert cur.fetchone()[0] is True

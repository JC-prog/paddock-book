import os

import psycopg
import pytest


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


def test_users_table_has_an_is_admin_column_defaulting_to_false(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'is_admin'
            """
        )
        row = cur.fetchone()

    assert row is not None, "users.is_admin column does not exist"
    data_type, column_default = row
    assert data_type == "boolean"
    assert column_default is not None and "false" in column_default.lower()


def test_app_settings_table_exists_with_expected_columns(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'app_settings'
            ORDER BY column_name
            """
        )
        rows = cur.fetchall()

    columns = {name: data_type for name, data_type in rows}
    assert columns.get("id") == "smallint"
    assert columns.get("log_to_file") == "boolean"


def test_app_settings_is_genuinely_a_single_row_table(conn):
    # Deliberately never commits — the fixture rolls everything back, so
    # this doesn't leave a real row behind for other tests/features that
    # rely on "no row yet" meaning the .env-based default applies.
    with conn.cursor() as cur:
        cur.execute("INSERT INTO app_settings (id, log_to_file) VALUES (1, true)")
        with pytest.raises(psycopg.errors.UniqueViolation):
            cur.execute("INSERT INTO app_settings (id, log_to_file) VALUES (1, false)")
        conn.rollback()

        cur.execute("INSERT INTO app_settings (id, log_to_file) VALUES (1, true)")
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute("INSERT INTO app_settings (id, log_to_file) VALUES (2, false)")
    conn.rollback()

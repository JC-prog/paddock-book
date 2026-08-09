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


def test_job_runs_table_exists_with_expected_columns(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'job_runs'
            ORDER BY column_name
            """
        )
        rows = cur.fetchall()

    columns = {name: data_type for name, data_type in rows}
    assert columns.get("id") == "uuid"
    assert columns.get("job_type") == "text"
    assert columns.get("target") == "text"
    assert columns.get("status") == "text"
    assert columns.get("params") == "jsonb"
    assert columns.get("result") == "jsonb"
    assert columns.get("error") == "text"
    assert columns.get("triggered_by_email") == "text"
    assert columns.get("created_at") == "timestamp with time zone"
    assert columns.get("started_at") == "timestamp with time zone"
    assert columns.get("finished_at") == "timestamp with time zone"


def test_job_runs_status_defaults_to_queued(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO job_runs (job_type, target, params, triggered_by_email)
            VALUES ('download', 'test-target-1', '{}'::jsonb, 'admin@team.example')
            RETURNING status
            """
        )
        status = cur.fetchone()[0]
    conn.rollback()

    assert status == "queued"


def test_job_runs_rejects_an_invalid_job_type(conn):
    with conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO job_runs (job_type, target, params, triggered_by_email)
                VALUES ('bogus', 'test-target-2', '{}'::jsonb, 'admin@team.example')
                """
            )
    conn.rollback()


def test_job_runs_rejects_an_invalid_status(conn):
    with conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO job_runs (job_type, target, params, status, triggered_by_email)
                VALUES ('download', 'test-target-3', '{}'::jsonb, 'bogus', 'admin@team.example')
                """
            )
    conn.rollback()


def test_active_target_uniq_index_blocks_a_second_active_job_for_the_same_target(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO job_runs (job_type, target, params, triggered_by_email)
            VALUES ('download', 'dup-target', '{}'::jsonb, 'admin@team.example')
            """
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO job_runs (job_type, target, params, triggered_by_email)
                VALUES ('download', 'dup-target', '{}'::jsonb, 'admin@team.example')
                """
            )
    conn.rollback()


def test_active_target_uniq_index_allows_a_new_job_once_the_prior_one_is_final(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO job_runs (job_type, target, params, status, triggered_by_email)
            VALUES ('download', 'dup-target-2', '{}'::jsonb, 'succeeded', 'admin@team.example')
            """
        )
        cur.execute(
            """
            INSERT INTO job_runs (job_type, target, params, triggered_by_email)
            VALUES ('download', 'dup-target-2', '{}'::jsonb, 'admin@team.example')
            """
        )
    conn.rollback()

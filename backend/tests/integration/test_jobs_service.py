import os
import uuid
from unittest.mock import MagicMock

import psycopg
import pytest

from src.modules.jobs.repository import list_jobs
from src.modules.jobs.service import trigger_download_job, trigger_ingest_job


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


def test_jobs_triggered_by_different_admins_are_both_visible_with_correct_attribution(conn):
    # trigger_download_job()/trigger_ingest_job() genuinely commit (by
    # design — a triggered job must be immediately visible to any admin,
    # even if the request that triggered it later fails for an unrelated
    # reason), so this test's rows survive the fixture's rollback() and
    # must be cleaned up explicitly, same as test_auth_api.py's pattern
    # for tests that exercise a real commit.
    target = f"svc-test-{uuid.uuid4()}"
    admin_a = {"sub": "a", "email": "admin-a@team.example", "department": "sporting", "is_admin": True}
    admin_b = {"sub": "b", "email": "admin-b@team.example", "department": "sporting", "is_admin": True}

    download_job = trigger_download_job(
        target, conn=conn, admin_user=admin_a, enqueue=MagicMock()
    )
    ingest_job = trigger_ingest_job(
        target, "sporting", conn=conn, admin_user=admin_b, enqueue=MagicMock()
    )

    try:
        jobs = list_jobs(conn)
        by_id = {j["id"]: j for j in jobs}

        assert by_id[download_job["id"]]["triggered_by_email"] == "admin-a@team.example"
        assert by_id[ingest_job["id"]]["triggered_by_email"] == "admin-b@team.example"
        assert by_id[download_job["id"]]["job_type"] == "download"
        assert by_id[ingest_job["id"]]["job_type"] == "ingest"
    finally:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM job_runs WHERE id IN (%s, %s)",
                (download_job["id"], ingest_job["id"]),
            )
        conn.commit()

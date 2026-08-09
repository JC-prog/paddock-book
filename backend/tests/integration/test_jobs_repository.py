import os

import psycopg
import pytest

from src.modules.jobs.repository import (
    DuplicateJobError,
    insert_job,
    list_jobs,
    mark_finished,
    mark_running,
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


def test_insert_job_creates_a_queued_row_and_returns_it(conn):
    job = insert_job(
        conn,
        job_type="download",
        target="repo-test-1",
        params={"category_id": "repo-test-1"},
        triggered_by_email="admin@team.example",
    )

    assert job["job_type"] == "download"
    assert job["target"] == "repo-test-1"
    assert job["status"] == "queued"
    assert job["params"] == {"category_id": "repo-test-1"}
    assert job["result"] is None
    assert job["error"] is None
    assert job["triggered_by_email"] == "admin@team.example"
    assert job["id"] is not None


def test_insert_job_raises_duplicate_job_error_for_an_active_duplicate(conn):
    insert_job(
        conn,
        job_type="download",
        target="repo-test-dup",
        params={},
        triggered_by_email="admin@team.example",
    )

    with pytest.raises(DuplicateJobError):
        insert_job(
            conn,
            job_type="download",
            target="repo-test-dup",
            params={},
            triggered_by_email="admin@team.example",
        )


def test_insert_job_allows_a_new_job_once_the_prior_one_reached_a_final_status(conn):
    first = insert_job(
        conn,
        job_type="ingest",
        target="repo-test-final",
        params={},
        triggered_by_email="admin@team.example",
    )
    mark_finished(conn, first["id"], status="succeeded", result={"ingested": 1, "skipped": 0, "failed": 0})

    second = insert_job(
        conn,
        job_type="ingest",
        target="repo-test-final",
        params={},
        triggered_by_email="admin@team.example",
    )

    assert second["id"] != first["id"]


def test_mark_running_sets_status_and_started_at(conn):
    job = insert_job(
        conn, job_type="download", target="repo-test-run", params={}, triggered_by_email="admin@team.example"
    )

    mark_running(conn, job["id"])

    updated = next(j for j in list_jobs(conn) if j["id"] == job["id"])
    assert updated["status"] == "running"
    assert updated["started_at"] is not None


def test_mark_finished_sets_status_result_and_finished_at(conn):
    job = insert_job(
        conn, job_type="download", target="repo-test-fin", params={}, triggered_by_email="admin@team.example"
    )
    mark_running(conn, job["id"])

    mark_finished(
        conn, job["id"], status="succeeded", result={"downloaded": 3, "skipped": 1, "failed": 0}
    )

    updated = next(j for j in list_jobs(conn) if j["id"] == job["id"])
    assert updated["status"] == "succeeded"
    assert updated["result"] == {"downloaded": 3, "skipped": 1, "failed": 0}
    assert updated["finished_at"] is not None


def test_mark_finished_records_a_top_level_error(conn):
    job = insert_job(
        conn, job_type="download", target="repo-test-err", params={}, triggered_by_email="admin@team.example"
    )

    mark_finished(conn, job["id"], status="failed", error="category does not exist")

    updated = next(j for j in list_jobs(conn) if j["id"] == job["id"])
    assert updated["status"] == "failed"
    assert updated["error"] == "category does not exist"
    assert updated["result"] is None


def test_list_jobs_returns_every_job_newest_first_regardless_of_who_triggered_it(conn):
    first = insert_job(
        conn, job_type="download", target="repo-test-list-1", params={}, triggered_by_email="admin-a@team.example"
    )
    second = insert_job(
        conn, job_type="ingest", target="repo-test-list-2", params={}, triggered_by_email="admin-b@team.example"
    )

    jobs = list_jobs(conn)
    ids_in_order = [j["id"] for j in jobs]

    assert ids_in_order.index(second["id"]) < ids_in_order.index(first["id"])
    emails = {j["id"]: j["triggered_by_email"] for j in jobs}
    assert emails[first["id"]] == "admin-a@team.example"
    assert emails[second["id"]] == "admin-b@team.example"

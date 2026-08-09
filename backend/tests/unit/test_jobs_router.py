from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.security import get_current_user
from src.main import app

client = TestClient(app)

_FAKE_ADMIN = {"sub": "admin-1", "email": "admin@team.example", "department": "sporting", "is_admin": True}
_FAKE_NON_ADMIN = {
    "sub": "user-1",
    "email": "driver@team.example",
    "department": "sporting",
    "is_admin": False,
}

_SAMPLE_JOB = {
    "id": "job-1",
    "job_type": "download",
    "target": "110",
    "status": "queued",
    "params": {"category_id": "110"},
    "result": None,
    "error": None,
    "triggered_by_email": "admin@team.example",
    "created_at": "2026-08-09T10:00:00Z",
    "started_at": None,
    "finished_at": None,
}


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def _as_admin():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_ADMIN


def _as_non_admin():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_NON_ADMIN


def test_list_jobs_rejects_unauthenticated_requests():
    response = client.get("/v1/admin/jobs")

    assert response.status_code == 401


def test_list_jobs_rejects_a_non_admin():
    _as_non_admin()

    response = client.get("/v1/admin/jobs")

    assert response.status_code == 403


def test_list_jobs_returns_the_repositorys_list_for_an_admin():
    _as_admin()

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.list_jobs", return_value=[_SAMPLE_JOB]),
    ):
        response = client.get("/v1/admin/jobs")

    assert response.status_code == 200
    assert response.json() == [_SAMPLE_JOB]


def test_list_jobs_preserves_the_repositorys_newest_first_order():
    _as_admin()
    older = {**_SAMPLE_JOB, "id": "job-older"}
    newer = {**_SAMPLE_JOB, "id": "job-newer"}

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.list_jobs", return_value=[newer, older]),
    ):
        response = client.get("/v1/admin/jobs")

    assert [job["id"] for job in response.json()] == ["job-newer", "job-older"]


def test_post_download_job_rejects_unauthenticated_requests():
    response = client.post("/v1/admin/jobs/download", json={"category_id": "110"})

    assert response.status_code == 401


def test_post_download_job_rejects_a_non_admin():
    _as_non_admin()

    response = client.post("/v1/admin/jobs/download", json={"category_id": "110"})

    assert response.status_code == 403


def test_post_download_job_returns_201_with_the_created_job_for_an_admin():
    _as_admin()

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_download_job", return_value=_SAMPLE_JOB) as mock_trigger,
    ):
        response = client.post("/v1/admin/jobs/download", json={"category_id": "110"})

    assert response.status_code == 201
    assert response.json() == _SAMPLE_JOB
    mock_trigger.assert_called_once()


def test_post_download_job_rejects_a_missing_category_id():
    _as_admin()

    response = client.post("/v1/admin/jobs/download", json={})

    assert response.status_code == 422


def test_post_download_job_returns_409_for_a_duplicate():
    _as_admin()
    from src.modules.jobs.repository import DuplicateJobError

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_download_job", side_effect=DuplicateJobError("dup")),
    ):
        response = client.post("/v1/admin/jobs/download", json={"category_id": "110"})

    assert response.status_code == 409


def test_post_download_job_returns_502_when_enqueue_fails():
    _as_admin()
    from src.modules.jobs.service import EnqueueError

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_download_job", side_effect=EnqueueError("no broker")),
    ):
        response = client.post("/v1/admin/jobs/download", json={"category_id": "110"})

    assert response.status_code == 502


_SAMPLE_INGEST_JOB = {**_SAMPLE_JOB, "id": "job-2", "job_type": "ingest", "target": "110"}


def test_post_ingest_job_rejects_unauthenticated_requests():
    response = client.post("/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "sporting"})

    assert response.status_code == 401


def test_post_ingest_job_rejects_a_non_admin():
    _as_non_admin()

    response = client.post("/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "sporting"})

    assert response.status_code == 403


def test_post_ingest_job_returns_201_with_the_created_job_for_an_admin():
    _as_admin()

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_ingest_job", return_value=_SAMPLE_INGEST_JOB) as mock_trigger,
    ):
        response = client.post("/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "sporting"})

    assert response.status_code == 201
    assert response.json() == _SAMPLE_INGEST_JOB
    mock_trigger.assert_called_once()


def test_post_ingest_job_rejects_a_missing_field():
    _as_admin()

    response = client.post("/v1/admin/jobs/ingest", json={"subfolder": "110"})

    assert response.status_code == 422


def test_post_ingest_job_rejects_an_unsupported_department():
    _as_admin()

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_ingest_job", side_effect=ValueError("bad department")),
    ):
        response = client.post(
            "/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "marketing"}
        )

    assert response.status_code == 422


def test_post_ingest_job_returns_400_for_an_invalid_subfolder():
    _as_admin()
    from src.modules.jobs.service import InvalidSubfolderError

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_ingest_job", side_effect=InvalidSubfolderError("bad path")),
    ):
        response = client.post(
            "/v1/admin/jobs/ingest", json={"subfolder": "../../etc", "department": "sporting"}
        )

    assert response.status_code == 400


def test_post_ingest_job_returns_409_for_a_duplicate():
    _as_admin()
    from src.modules.jobs.repository import DuplicateJobError

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_ingest_job", side_effect=DuplicateJobError("dup")),
    ):
        response = client.post(
            "/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "sporting"}
        )

    assert response.status_code == 409


def test_post_ingest_job_returns_502_when_enqueue_fails():
    _as_admin()
    from src.modules.jobs.service import EnqueueError

    with (
        patch("src.modules.jobs.router.get_connection", MagicMock()),
        patch("src.modules.jobs.router.trigger_ingest_job", side_effect=EnqueueError("no broker")),
    ):
        response = client.post(
            "/v1/admin/jobs/ingest", json={"subfolder": "110", "department": "sporting"}
        )

    assert response.status_code == 502

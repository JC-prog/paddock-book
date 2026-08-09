from unittest.mock import MagicMock

import pytest

from src.modules.download.repository import ManifestEntry
from src.modules.download.service import DownloadFailure, DownloadRunResult
from src.modules.jobs import repository as real_repository
from src.modules.jobs.repository import DuplicateJobError
from src.modules.jobs.service import (
    REGULATIONS_ROOT,
    EnqueueError,
    InvalidSubfolderError,
    execute_download_job,
    execute_ingest_job,
    resolve_ingest_subfolder,
    trigger_download_job,
    trigger_ingest_job,
)

_ADMIN_USER = {"sub": "admin-1", "email": "admin@team.example", "department": "sporting", "is_admin": True}

_QUEUED_JOB = {
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


def test_trigger_download_job_inserts_a_job_and_enqueues_it():
    repository = MagicMock(spec=real_repository)
    repository.insert_job.return_value = _QUEUED_JOB
    enqueue = MagicMock()
    conn = MagicMock()

    job = trigger_download_job(
        "110", conn=conn, admin_user=_ADMIN_USER, repository=repository, enqueue=enqueue
    )

    repository.insert_job.assert_called_once_with(
        conn,
        job_type="download",
        target="110",
        params={"category_id": "110"},
        triggered_by_email="admin@team.example",
    )
    conn.commit.assert_called_once()
    enqueue.assert_called_once_with("job-1")
    assert job == _QUEUED_JOB


def test_trigger_download_job_propagates_a_duplicate_job_error():
    repository = MagicMock(spec=real_repository)
    repository.insert_job.side_effect = DuplicateJobError("already queued")
    enqueue = MagicMock()

    with pytest.raises(DuplicateJobError):
        trigger_download_job(
            "110", conn=MagicMock(), admin_user=_ADMIN_USER, repository=repository, enqueue=enqueue
        )

    enqueue.assert_not_called()


def test_trigger_download_job_marks_the_job_failed_when_enqueue_raises():
    repository = MagicMock(spec=real_repository)
    repository.insert_job.return_value = _QUEUED_JOB
    enqueue = MagicMock(side_effect=RuntimeError("no broker"))
    conn = MagicMock()

    with pytest.raises(EnqueueError):
        trigger_download_job(
            "110", conn=conn, admin_user=_ADMIN_USER, repository=repository, enqueue=enqueue
        )

    repository.mark_finished.assert_called_once()
    args, kwargs = repository.mark_finished.call_args
    assert args[1] == "job-1"
    assert kwargs["status"] == "failed"
    assert "no broker" in kwargs["error"]
    assert conn.commit.call_count == 2


def test_execute_download_job_marks_running_then_succeeded_with_counts():
    repository = MagicMock(spec=real_repository)
    connection_factory = MagicMock()
    conn = connection_factory.return_value
    run_result = DownloadRunResult(
        downloaded=[
            ManifestEntry(
                title="Sporting Regs",
                source_url="https://fia.example/a.pdf",
                section="Sporting",
                issue="1",
                published_date="2026-01-01",
                local_filename="a.pdf",
                downloaded_at="2026-08-09T10:00:00Z",
            )
        ],
        skipped=["https://fia.example/b.pdf"],
        failed=[DownloadFailure(source_url="https://fia.example/c.pdf", title="C", reason="timeout")],
    )
    download = MagicMock(return_value=run_result)

    execute_download_job(
        "job-1", "110", connection_factory=connection_factory, repository=repository, download=download
    )

    repository.mark_running.assert_called_once_with(conn, "job-1")
    download.assert_called_once()
    args, kwargs = download.call_args
    assert args[0] == "110"
    assert str(args[1]) == "data/regulations/110"
    repository.mark_finished.assert_called_once_with(
        conn,
        "job-1",
        status="succeeded",
        result={
            "downloaded": 1,
            "skipped": 1,
            "failed": 1,
            "failures": [{"source_url": "https://fia.example/c.pdf", "title": "C", "reason": "timeout"}],
        },
    )
    conn.close.assert_called_once()


def test_resolve_ingest_subfolder_accepts_a_plain_subfolder_name():
    resolved = resolve_ingest_subfolder("110")

    assert resolved == (REGULATIONS_ROOT / "110").resolve()


def test_resolve_ingest_subfolder_rejects_parent_traversal():
    with pytest.raises(InvalidSubfolderError):
        resolve_ingest_subfolder("../../etc")


def test_resolve_ingest_subfolder_rejects_an_absolute_path():
    with pytest.raises(InvalidSubfolderError):
        resolve_ingest_subfolder("/etc/passwd")


def test_execute_download_job_marks_failed_when_download_category_raises():
    repository = MagicMock(spec=real_repository)
    connection_factory = MagicMock()
    conn = connection_factory.return_value
    download = MagicMock(side_effect=RuntimeError("category does not exist"))

    execute_download_job(
        "job-1", "not-real", connection_factory=connection_factory, repository=repository, download=download
    )

    repository.mark_finished.assert_called_once_with(
        conn, "job-1", status="failed", error="category does not exist"
    )
    conn.close.assert_called_once()


_QUEUED_INGEST_JOB = {
    "id": "job-2",
    "job_type": "ingest",
    "target": "110",
    "status": "queued",
    "params": {"subfolder": "110", "department": "sporting"},
    "result": None,
    "error": None,
    "triggered_by_email": "admin@team.example",
    "created_at": "2026-08-09T10:00:00Z",
    "started_at": None,
    "finished_at": None,
}


def test_trigger_ingest_job_rejects_an_invalid_subfolder_before_creating_a_job():
    repository = MagicMock(spec=real_repository)
    enqueue = MagicMock()

    with pytest.raises(InvalidSubfolderError):
        trigger_ingest_job(
            "../../etc",
            "sporting",
            conn=MagicMock(),
            admin_user=_ADMIN_USER,
            repository=repository,
            enqueue=enqueue,
        )

    repository.insert_job.assert_not_called()
    enqueue.assert_not_called()


def test_trigger_ingest_job_rejects_an_unsupported_department_before_creating_a_job():
    repository = MagicMock(spec=real_repository)
    enqueue = MagicMock()

    with pytest.raises(ValueError):
        trigger_ingest_job(
            "110",
            "marketing",
            conn=MagicMock(),
            admin_user=_ADMIN_USER,
            repository=repository,
            enqueue=enqueue,
        )

    repository.insert_job.assert_not_called()
    enqueue.assert_not_called()


def test_trigger_ingest_job_inserts_a_job_and_enqueues_it():
    repository = MagicMock(spec=real_repository)
    repository.insert_job.return_value = _QUEUED_INGEST_JOB
    enqueue = MagicMock()
    conn = MagicMock()

    job = trigger_ingest_job(
        "110", "sporting", conn=conn, admin_user=_ADMIN_USER, repository=repository, enqueue=enqueue
    )

    repository.insert_job.assert_called_once_with(
        conn,
        job_type="ingest",
        target="110",
        params={"subfolder": "110", "department": "sporting"},
        triggered_by_email="admin@team.example",
    )
    conn.commit.assert_called_once()
    enqueue.assert_called_once_with("job-2")
    assert job == _QUEUED_INGEST_JOB


def test_trigger_ingest_job_marks_the_job_failed_when_enqueue_raises():
    repository = MagicMock(spec=real_repository)
    repository.insert_job.return_value = _QUEUED_INGEST_JOB
    enqueue = MagicMock(side_effect=RuntimeError("no broker"))
    conn = MagicMock()

    with pytest.raises(EnqueueError):
        trigger_ingest_job(
            "110", "sporting", conn=conn, admin_user=_ADMIN_USER, repository=repository, enqueue=enqueue
        )

    repository.mark_finished.assert_called_once()
    assert conn.commit.call_count == 2


def _manifest_entry(title: str, local_filename: str) -> dict:
    return {
        "title": title,
        "source_url": f"https://fia.example/{local_filename}",
        "section": "Sporting",
        "issue": "1",
        "published_date": "2026-01-01",
        "local_filename": local_filename,
        "downloaded_at": "2026-08-09T10:00:00Z",
    }


def test_execute_ingest_job_skips_already_ingested_titles_without_calling_ingest():
    repository = MagicMock(spec=real_repository)
    connection_factory = MagicMock()
    load_manifest = MagicMock(
        return_value={"a": _manifest_entry("Already Here", "a.pdf")}
    )
    title_exists = MagicMock(return_value=True)
    ingest = MagicMock()

    execute_ingest_job(
        "job-2",
        "110",
        "sporting",
        connection_factory=connection_factory,
        repository=repository,
        load_manifest=load_manifest,
        title_exists=title_exists,
        ingest=ingest,
    )

    ingest.assert_not_called()
    repository.mark_finished.assert_called_once()
    _, kwargs = repository.mark_finished.call_args
    assert kwargs["result"] == {"ingested": 0, "skipped": 1, "failed": 0, "failures": []}


def test_execute_ingest_job_ingests_new_titles_and_continues_past_a_failure():
    repository = MagicMock(spec=real_repository)
    connection_factory = MagicMock()
    load_manifest = MagicMock(
        return_value={
            "a": _manifest_entry("Good Doc", "a.pdf"),
            "b": _manifest_entry("Bad Doc", "b.pdf"),
        }
    )
    title_exists = MagicMock(return_value=False)

    def _ingest(file_path, title, department):
        if title == "Bad Doc":
            raise RuntimeError("could not parse")

    execute_ingest_job(
        "job-2",
        "110",
        "sporting",
        connection_factory=connection_factory,
        repository=repository,
        load_manifest=load_manifest,
        title_exists=title_exists,
        ingest=_ingest,
    )

    repository.mark_finished.assert_called_once()
    _, kwargs = repository.mark_finished.call_args
    assert kwargs["result"] == {
        "ingested": 1,
        "skipped": 0,
        "failed": 1,
        "failures": [{"title": "Bad Doc", "reason": "could not parse"}],
    }

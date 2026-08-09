from pathlib import Path

from src.core.db import get_connection
from src.modules.download.repository import load_manifest as load_manifest_fn
from src.modules.download.service import download_category as download_category_fn
from src.modules.ingestion.repository import title_exists as title_exists_fn
from src.modules.ingestion.service import DEPARTMENTS
from src.modules.ingestion.service import ingest as ingest_fn
from src.modules.jobs import repository as repository_module

REGULATIONS_ROOT = Path("data/regulations")


class EnqueueError(Exception):
    pass


class InvalidSubfolderError(Exception):
    pass


def resolve_ingest_subfolder(subfolder: str) -> Path:
    base = REGULATIONS_ROOT.resolve()
    target = (REGULATIONS_ROOT / subfolder).resolve()
    if not target.is_relative_to(base):
        raise InvalidSubfolderError(f"{subfolder!r} is not a valid regulations subfolder")
    return target


def trigger_download_job(
    category_id: str, *, conn, admin_user: dict, repository=repository_module, enqueue
) -> dict:
    job = repository.insert_job(
        conn,
        job_type="download",
        target=category_id,
        params={"category_id": category_id},
        triggered_by_email=admin_user["email"],
    )
    conn.commit()

    try:
        enqueue(job["id"])
    except Exception as exc:
        repository.mark_finished(conn, job["id"], status="failed", error=str(exc))
        conn.commit()
        raise EnqueueError(f"could not enqueue download job {job['id']}") from exc

    return job


def execute_download_job(
    job_id: str,
    category_id: str,
    *,
    connection_factory=get_connection,
    repository=repository_module,
    download=download_category_fn,
) -> None:
    conn = connection_factory()
    try:
        repository.mark_running(conn, job_id)
        conn.commit()

        try:
            run_result = download(category_id, REGULATIONS_ROOT / category_id)
        except Exception as exc:
            repository.mark_finished(conn, job_id, status="failed", error=str(exc))
            conn.commit()
            return

        result = {
            "downloaded": len(run_result.downloaded),
            "skipped": len(run_result.skipped),
            "failed": len(run_result.failed),
            "failures": [
                {"source_url": f.source_url, "title": f.title, "reason": f.reason}
                for f in run_result.failed
            ],
        }
        repository.mark_finished(conn, job_id, status="succeeded", result=result)
        conn.commit()
    finally:
        conn.close()


def trigger_ingest_job(
    subfolder: str, department: str, *, conn, admin_user: dict, repository=repository_module, enqueue
) -> dict:
    resolve_ingest_subfolder(subfolder)
    if department not in DEPARTMENTS:
        raise ValueError(f"Unsupported department '{department}' — must be one of {sorted(DEPARTMENTS)}")

    job = repository.insert_job(
        conn,
        job_type="ingest",
        target=subfolder,
        params={"subfolder": subfolder, "department": department},
        triggered_by_email=admin_user["email"],
    )
    conn.commit()

    try:
        enqueue(job["id"])
    except Exception as exc:
        repository.mark_finished(conn, job["id"], status="failed", error=str(exc))
        conn.commit()
        raise EnqueueError(f"could not enqueue ingest job {job['id']}") from exc

    return job


def execute_ingest_job(
    job_id: str,
    subfolder: str,
    department: str,
    *,
    connection_factory=get_connection,
    repository=repository_module,
    load_manifest=load_manifest_fn,
    title_exists=title_exists_fn,
    ingest=ingest_fn,
) -> None:
    conn = connection_factory()
    try:
        repository.mark_running(conn, job_id)
        conn.commit()

        subfolder_path = REGULATIONS_ROOT / subfolder
        manifest = load_manifest(subfolder_path)

        ingested = 0
        skipped = 0
        failed = 0
        failures = []

        for entry in manifest.values():
            title = entry["title"]
            if title_exists(conn, title):
                skipped += 1
                continue

            file_path = subfolder_path / entry["local_filename"]
            try:
                ingest(str(file_path), title, department)
                ingested += 1
            except Exception as exc:
                failed += 1
                failures.append({"title": title, "reason": str(exc)})

        result = {"ingested": ingested, "skipped": skipped, "failed": failed, "failures": failures}
        repository.mark_finished(conn, job_id, status="succeeded", result=result)
        conn.commit()
    finally:
        conn.close()

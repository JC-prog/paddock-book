from fastapi import APIRouter, Depends, HTTPException, status

from src.core.db import get_connection
from src.core.security import require_admin
from src.modules.jobs.repository import DuplicateJobError, list_jobs
from src.modules.jobs.schemas import DownloadJobRequest, IngestJobRequest, JobRecord
from src.modules.jobs.service import (
    EnqueueError,
    InvalidSubfolderError,
    trigger_download_job,
    trigger_ingest_job,
)
from src.modules.jobs.tasks import run_download_job_task, run_ingest_job_task

router = APIRouter(prefix="/v1/admin/jobs")


@router.get("", response_model=list[JobRecord])
def get_jobs(admin_user: dict = Depends(require_admin)) -> list[JobRecord]:
    conn = get_connection()
    try:
        jobs = list_jobs(conn)
    finally:
        conn.close()
    return [JobRecord(**job) for job in jobs]


@router.post("/download", response_model=JobRecord, status_code=status.HTTP_201_CREATED)
def post_download_job(
    payload: DownloadJobRequest, admin_user: dict = Depends(require_admin)
) -> JobRecord:
    conn = get_connection()
    try:
        job = trigger_download_job(
            payload.category_id,
            conn=conn,
            admin_user=admin_user,
            enqueue=lambda job_id: run_download_job_task.delay(job_id, payload.category_id),
        )
    except DuplicateJobError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EnqueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        conn.close()
    return JobRecord(**job)


@router.post("/ingest", response_model=JobRecord, status_code=status.HTTP_201_CREATED)
def post_ingest_job(payload: IngestJobRequest, admin_user: dict = Depends(require_admin)) -> JobRecord:
    conn = get_connection()
    try:
        job = trigger_ingest_job(
            payload.subfolder,
            payload.department,
            conn=conn,
            admin_user=admin_user,
            enqueue=lambda job_id: run_ingest_job_task.delay(
                job_id, payload.subfolder, payload.department
            ),
        )
    except InvalidSubfolderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except DuplicateJobError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EnqueueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        conn.close()
    return JobRecord(**job)

from src.core.celery_app import celery_app
from src.modules.jobs import service as jobs_service


@celery_app.task(name="jobs.run_download_job")
def run_download_job_task(job_id: str, category_id: str) -> None:
    jobs_service.execute_download_job(job_id, category_id)


@celery_app.task(name="jobs.run_ingest_job")
def run_ingest_job_task(job_id: str, subfolder: str, department: str) -> None:
    jobs_service.execute_ingest_job(job_id, subfolder, department)

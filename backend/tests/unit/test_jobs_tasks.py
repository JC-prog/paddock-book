from unittest.mock import patch

from src.modules.jobs.tasks import run_download_job_task, run_ingest_job_task


def test_run_download_job_task_calls_execute_download_job():
    with patch("src.modules.jobs.tasks.jobs_service") as mock_service:
        run_download_job_task("job-1", "110")

    mock_service.execute_download_job.assert_called_once_with("job-1", "110")


def test_run_ingest_job_task_calls_execute_ingest_job():
    with patch("src.modules.jobs.tasks.jobs_service") as mock_service:
        run_ingest_job_task("job-2", "110", "sporting")

    mock_service.execute_ingest_job.assert_called_once_with("job-2", "110", "sporting")

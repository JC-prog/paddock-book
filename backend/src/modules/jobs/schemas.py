from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DownloadJobRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    category_id: str


class IngestJobRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    subfolder: str
    department: str


class JobRecord(BaseModel):
    id: str
    job_type: str
    target: str
    status: str
    params: dict
    result: dict | None
    error: str | None
    triggered_by_email: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

from fastapi import APIRouter

from src.modules.health.schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(status="ok")

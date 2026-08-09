from fastapi import APIRouter, Depends

from src.core.db import get_connection
from src.core.security import require_admin
from src.modules.admin.schemas import LogDestinationSetting
from src.modules.admin.service import get_log_destination, update_log_destination

router = APIRouter(prefix="/v1/admin")


@router.get("/settings/log-destination", response_model=LogDestinationSetting)
def get_setting(admin_user: dict = Depends(require_admin)) -> LogDestinationSetting:
    conn = get_connection()
    try:
        value = get_log_destination(conn=conn)
    finally:
        conn.close()
    return LogDestinationSetting(log_to_file=value)


@router.put("/settings/log-destination", response_model=LogDestinationSetting)
def put_setting(
    payload: LogDestinationSetting, admin_user: dict = Depends(require_admin)
) -> LogDestinationSetting:
    conn = get_connection()
    try:
        value = update_log_destination(payload.log_to_file, conn=conn, admin_user=admin_user)
    finally:
        conn.close()
    return LogDestinationSetting(log_to_file=value)

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.db import get_connection
from src.core.security import require_admin
from src.modules.admin.schemas import (
    ChatProviderSettingsResponse,
    ChatProviderSettingsUpdate,
    LogDestinationSetting,
)
from src.modules.admin.service import (
    IncompleteProviderConfigError,
    get_chat_provider_config,
    get_log_destination,
    update_chat_provider_config,
    update_log_destination,
)

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


@router.get("/settings/chat-provider", response_model=ChatProviderSettingsResponse)
def get_chat_provider_setting(
    admin_user: dict = Depends(require_admin),
) -> ChatProviderSettingsResponse:
    conn = get_connection()
    try:
        result = get_chat_provider_config(conn=conn)
    finally:
        conn.close()
    return ChatProviderSettingsResponse(**result)


@router.put("/settings/chat-provider", response_model=ChatProviderSettingsResponse)
def put_chat_provider_setting(
    payload: ChatProviderSettingsUpdate, admin_user: dict = Depends(require_admin)
) -> ChatProviderSettingsResponse:
    # Partial update (contracts/admin-api.md): only fields the admin
    # actually sent are changed — exclude_unset distinguishes "omitted"
    # from "explicitly null", unlike a plain .model_dump().
    updates = payload.model_dump(exclude_unset=True)

    conn = get_connection()
    try:
        result = update_chat_provider_config(updates, conn=conn, admin_user=admin_user)
    except IncompleteProviderConfigError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    finally:
        conn.close()
    return ChatProviderSettingsResponse(**result)

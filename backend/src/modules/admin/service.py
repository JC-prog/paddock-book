import logging

from src.core.config import Settings
from src.modules.admin import repository as repository_module

logger = logging.getLogger(__name__)


def get_log_destination(
    *, conn, repository=repository_module, settings_factory=Settings
) -> bool:
    value = repository.get_log_destination_setting(conn)
    if value is not None:
        return value

    return settings_factory().log_to_file


def promote_account(email: str, *, conn, repository=repository_module) -> dict:
    promoted = repository.promote_to_admin(conn, email)
    if promoted is None:
        raise ValueError(f"no account found for email {email!r}")

    conn.commit()

    logger.info(
        "admin access granted",
        extra={
            "event": "admin_granted",
            "promoted_user_id": promoted["id"],
            "promoted_email": promoted["email"],
        },
    )
    return promoted


def update_log_destination(
    new_value: bool, *, conn, admin_user: dict, repository=repository_module
) -> bool:
    repository.set_log_destination_setting(conn, new_value)
    conn.commit()

    logger.info(
        "log destination changed",
        extra={
            "event": "log_destination_changed",
            "admin_user_id": admin_user["sub"],
            "new_value": new_value,
        },
    )
    return new_value

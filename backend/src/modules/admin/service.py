import logging

from src.core.config import Settings
from src.modules.admin import repository as repository_module

logger = logging.getLogger(__name__)

_CHAT_PROVIDER_DEFAULTS = {
    "active_provider": "ollama",
    "ollama_model_override": None,
    "bedrock_model": None,
    "openai_compatible_base_url": None,
    "openai_compatible_model": None,
    "openai_compatible_api_key_set": False,
}


class IncompleteProviderConfigError(Exception):
    """Raised when a PUT would activate a provider that's missing
    required settings (FR-012/FR-013) — see research.md's "validation in
    the service layer, not a DB constraint" decision."""


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


_CHAT_PROVIDER_ROW_DEFAULTS = {
    "active_provider": "ollama",
    "ollama_model_override": None,
    "bedrock_model": None,
    "openai_compatible_base_url": None,
    "openai_compatible_api_key": None,
    "openai_compatible_model": None,
}


def _validate_activation(resulting_row: dict) -> None:
    """Checked against the merged (current + this update) row, not just
    this request's body — so activating a provider configured in an
    earlier call still passes (FR-015). Ollama needs nothing."""
    provider = resulting_row["active_provider"]
    if provider == "ollama":
        return

    if provider == "bedrock" and not resulting_row.get("bedrock_model"):
        raise IncompleteProviderConfigError(
            "bedrock requires a model identifier before it can be activated"
        )

    if provider == "openai_compatible":
        required = (
            "openai_compatible_base_url",
            "openai_compatible_api_key",
            "openai_compatible_model",
        )
        if not all(resulting_row.get(field) for field in required):
            raise IncompleteProviderConfigError(
                "openai_compatible requires a base URL, API key, and model name "
                "before it can be activated"
            )


def update_chat_provider_config(
    updates: dict, *, conn, admin_user: dict, repository=repository_module
) -> dict:
    current = repository.get_chat_provider_settings(conn) or _CHAT_PROVIDER_ROW_DEFAULTS
    resulting_row = {**current, **updates}
    _validate_activation(resulting_row)

    repository.upsert_chat_provider_settings(conn, updates)
    conn.commit()

    logger.info(
        "chat provider config changed",
        extra={
            "event": "chat_provider_config_changed",
            "admin_user_id": admin_user["sub"],
            "new_active_provider": updates.get("active_provider"),
        },
    )
    return get_chat_provider_config(conn=conn, repository=repository)


def get_chat_provider_config(*, conn, repository=repository_module) -> dict:
    row = repository.get_chat_provider_settings(conn)
    if row is None:
        return dict(_CHAT_PROVIDER_DEFAULTS)

    return {
        "active_provider": row["active_provider"],
        "ollama_model_override": row["ollama_model_override"],
        "bedrock_model": row["bedrock_model"],
        "openai_compatible_base_url": row["openai_compatible_base_url"],
        "openai_compatible_model": row["openai_compatible_model"],
        "openai_compatible_api_key_set": row["openai_compatible_api_key"] is not None,
    }

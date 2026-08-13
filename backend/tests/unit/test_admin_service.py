import logging

import pytest
from unittest.mock import MagicMock

from src.modules.admin import repository as real_repository
from src.modules.admin.service import (
    IncompleteProviderConfigError,
    get_chat_provider_config,
    get_log_destination,
    promote_account,
    update_chat_provider_config,
    update_log_destination,
)


def _event_record(caplog, event: str) -> logging.LogRecord:
    return next(r for r in caplog.records if getattr(r, "event", None) == event)


def _admin_user(**overrides):
    defaults = {"sub": "admin-1", "email": "admin@team.example", "department": "sporting", "is_admin": True}
    defaults.update(overrides)
    return defaults


def test_get_log_destination_returns_the_stored_value_when_a_row_exists():
    repository = MagicMock(spec=real_repository)
    repository.get_log_destination_setting.return_value = False

    result = get_log_destination(conn=MagicMock(), repository=repository)

    assert result is False


def test_get_log_destination_falls_back_to_the_env_based_default_when_no_row_exists():
    repository = MagicMock(spec=real_repository)
    repository.get_log_destination_setting.return_value = None
    settings_factory = MagicMock(return_value=MagicMock(log_to_file=True))

    result = get_log_destination(conn=MagicMock(), repository=repository, settings_factory=settings_factory)

    assert result is True


def test_update_log_destination_calls_the_repository_setter():
    repository = MagicMock(spec=real_repository)

    update_log_destination(False, conn=MagicMock(), admin_user=_admin_user(), repository=repository)

    repository.set_log_destination_setting.assert_called_once()
    args, _ = repository.set_log_destination_setting.call_args
    assert args[1] is False


def test_update_log_destination_logs_a_log_destination_changed_event(caplog):
    caplog.set_level(logging.INFO)
    repository = MagicMock(spec=real_repository)

    update_log_destination(
        False, conn=MagicMock(), admin_user=_admin_user(sub="admin-42"), repository=repository
    )

    record = _event_record(caplog, "log_destination_changed")
    assert record.admin_user_id == "admin-42"
    assert record.new_value is False


def test_update_log_destination_returns_the_new_value():
    repository = MagicMock(spec=real_repository)

    result = update_log_destination(True, conn=MagicMock(), admin_user=_admin_user(), repository=repository)

    assert result is True


def test_promote_account_logs_an_admin_granted_event_on_success(caplog):
    caplog.set_level(logging.INFO)
    repository = MagicMock(spec=real_repository)
    repository.promote_to_admin.return_value = {"id": "u1", "email": "driver@team.example"}

    promote_account("driver@team.example", conn=MagicMock(), repository=repository)

    record = _event_record(caplog, "admin_granted")
    assert record.promoted_user_id == "u1"
    assert record.promoted_email == "driver@team.example"


def test_promote_account_raises_value_error_and_logs_nothing_for_an_unknown_email(caplog):
    caplog.set_level(logging.INFO)
    repository = MagicMock(spec=real_repository)
    repository.promote_to_admin.return_value = None

    with pytest.raises(ValueError):
        promote_account("nobody@team.example", conn=MagicMock(), repository=repository)

    assert not any(getattr(r, "event", None) == "admin_granted" for r in caplog.records)


def test_get_chat_provider_config_returns_defaults_when_no_row_exists():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    result = get_chat_provider_config(conn=MagicMock(), repository=repository)

    assert result == {
        "active_provider": "ollama",
        "ollama_model_override": None,
        "bedrock_model": None,
        "openai_compatible_base_url": None,
        "openai_compatible_model": None,
        "openai_compatible_api_key_set": False,
    }


def test_get_chat_provider_config_reports_key_set_without_the_key_value():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = {
        "active_provider": "openai_compatible",
        "ollama_model_override": None,
        "bedrock_model": None,
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "sk-real-secret-value",
        "openai_compatible_model": "gpt-4o-mini",
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = get_chat_provider_config(conn=MagicMock(), repository=repository)

    assert result["openai_compatible_api_key_set"] is True
    assert "openai_compatible_api_key" not in result
    assert "sk-real-secret-value" not in str(result)
    assert result["active_provider"] == "openai_compatible"
    assert result["openai_compatible_base_url"] == "https://api.openai.com/v1"
    assert result["openai_compatible_model"] == "gpt-4o-mini"


def test_update_chat_provider_config_allows_ollama_regardless_of_other_stored_data():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    update_chat_provider_config(
        {"active_provider": "ollama"}, conn=MagicMock(), admin_user=_admin_user(), repository=repository
    )

    repository.upsert_chat_provider_settings.assert_called_once()


def test_update_chat_provider_config_calls_upsert_with_exactly_the_callers_updates():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None
    conn = MagicMock()
    updates = {"active_provider": "ollama", "ollama_model_override": "llama3.3"}

    update_chat_provider_config(updates, conn=conn, admin_user=_admin_user(), repository=repository)

    args, _ = repository.upsert_chat_provider_settings.call_args
    assert args == (conn, updates)


def test_update_chat_provider_config_commits_on_success():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None
    conn = MagicMock()

    update_chat_provider_config({"active_provider": "ollama"}, conn=conn, admin_user=_admin_user(), repository=repository)

    conn.commit.assert_called_once()


def test_update_chat_provider_config_logs_event_without_the_api_key_value(caplog):
    caplog.set_level(logging.INFO)
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    update_chat_provider_config(
        {"active_provider": "ollama", "openai_compatible_api_key": "sk-should-not-be-logged"},
        conn=MagicMock(),
        admin_user=_admin_user(sub="admin-42"),
        repository=repository,
    )

    record = _event_record(caplog, "chat_provider_config_changed")
    assert record.admin_user_id == "admin-42"
    assert "sk-should-not-be-logged" not in str(record.__dict__)


def test_update_chat_provider_config_returns_the_fresh_config():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": "llama3.3",
        "bedrock_model": None,
        "openai_compatible_base_url": None,
        "openai_compatible_api_key": None,
        "openai_compatible_model": None,
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = update_chat_provider_config(
        {"active_provider": "ollama"}, conn=MagicMock(), admin_user=_admin_user(), repository=repository
    )

    assert result["active_provider"] == "ollama"
    assert result["ollama_model_override"] == "llama3.3"


def test_update_chat_provider_config_blocks_bedrock_activation_without_a_model():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    with pytest.raises(IncompleteProviderConfigError):
        update_chat_provider_config(
            {"active_provider": "bedrock"}, conn=MagicMock(), admin_user=_admin_user(), repository=repository
        )

    repository.upsert_chat_provider_settings.assert_not_called()


def test_update_chat_provider_config_allows_bedrock_activation_with_a_model_in_the_same_update():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    update_chat_provider_config(
        {"active_provider": "bedrock", "bedrock_model": "anthropic.claude-3-5-sonnet-v2"},
        conn=MagicMock(),
        admin_user=_admin_user(),
        repository=repository,
    )

    repository.upsert_chat_provider_settings.assert_called_once()


def test_update_chat_provider_config_allows_bedrock_activation_when_model_was_previously_saved():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": None,
        "bedrock_model": "anthropic.claude-3-5-sonnet-v2",
        "openai_compatible_base_url": None,
        "openai_compatible_api_key": None,
        "openai_compatible_model": None,
        "updated_at": "2026-08-12T00:00:00Z",
    }

    update_chat_provider_config(
        {"active_provider": "bedrock"}, conn=MagicMock(), admin_user=_admin_user(), repository=repository
    )

    repository.upsert_chat_provider_settings.assert_called_once()


def test_update_chat_provider_config_blocks_openai_compatible_activation_when_incomplete():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    with pytest.raises(IncompleteProviderConfigError):
        update_chat_provider_config(
            {"active_provider": "openai_compatible", "openai_compatible_base_url": "https://api.openai.com/v1"},
            conn=MagicMock(),
            admin_user=_admin_user(),
            repository=repository,
        )

    repository.upsert_chat_provider_settings.assert_not_called()


def test_update_chat_provider_config_allows_openai_compatible_activation_with_all_three_fields():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = None

    update_chat_provider_config(
        {
            "active_provider": "openai_compatible",
            "openai_compatible_base_url": "https://api.openai.com/v1",
            "openai_compatible_api_key": "sk-test",
            "openai_compatible_model": "gpt-4o-mini",
        },
        conn=MagicMock(),
        admin_user=_admin_user(),
        repository=repository,
    )

    repository.upsert_chat_provider_settings.assert_called_once()


def test_update_chat_provider_config_allows_openai_compatible_activation_when_previously_saved():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": None,
        "bedrock_model": None,
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "sk-test",
        "openai_compatible_model": "gpt-4o-mini",
        "updated_at": "2026-08-12T00:00:00Z",
    }

    update_chat_provider_config(
        {"active_provider": "openai_compatible"}, conn=MagicMock(), admin_user=_admin_user(), repository=repository
    )

    repository.upsert_chat_provider_settings.assert_called_once()


def test_get_chat_provider_config_reports_key_not_set_when_none_saved():
    repository = MagicMock(spec=real_repository)
    repository.get_chat_provider_settings.return_value = {
        "active_provider": "ollama",
        "ollama_model_override": "llama3.3",
        "bedrock_model": None,
        "openai_compatible_base_url": None,
        "openai_compatible_api_key": None,
        "openai_compatible_model": None,
        "updated_at": "2026-08-12T00:00:00Z",
    }

    result = get_chat_provider_config(conn=MagicMock(), repository=repository)

    assert result["openai_compatible_api_key_set"] is False
    assert result["ollama_model_override"] == "llama3.3"

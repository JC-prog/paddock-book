import logging

import pytest
from unittest.mock import MagicMock

from src.modules.admin import repository as real_repository
from src.modules.admin.service import get_log_destination, promote_account, update_log_destination


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

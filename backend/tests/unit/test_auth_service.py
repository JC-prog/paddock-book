import logging
from unittest.mock import MagicMock

import pytest

from src.core import security as real_security
from src.modules.auth import repository as real_repository
from src.modules.auth.service import login, logout, refresh_access_token, register


def _settings_factory(**overrides):
    defaults = {"jwt_secret": "test-secret", "access_token_ttl_minutes": 15, "refresh_token_ttl_days": 7}
    defaults.update(overrides)
    return MagicMock(return_value=MagicMock(**defaults))


def _collaborators(user=None, valid_refresh=None, created_user=None):
    repository = MagicMock(spec=real_repository)
    repository.get_user_by_email.return_value = user
    repository.get_valid_refresh_token.return_value = valid_refresh
    repository.get_user_by_id.return_value = user
    repository.create_user.return_value = created_user or _user()

    security = MagicMock(spec=real_security)
    security.verify_password.side_effect = lambda password, password_hash: password == "correct-password"
    security.hash_password.return_value = "a-hashed-password"
    security.create_access_token.return_value = "an-access-token"
    security.generate_refresh_token.return_value = "a-raw-refresh-token"
    security.hash_token.return_value = "a-hashed-refresh-token"

    conn = MagicMock()
    settings_factory = _settings_factory()

    return {
        "repository": repository,
        "security": security,
        "conn": conn,
        "settings_factory": settings_factory,
    }


def _user(**overrides):
    defaults = {
        "id": "user-123",
        "email": "driver@team.example",
        "password_hash": "hashed",
        "department": "sporting",
    }
    defaults.update(overrides)
    return defaults


def test_login_returns_tokens_for_valid_credentials():
    collaborators = _collaborators(user=_user())

    result = login("driver@team.example", "correct-password", **collaborators)

    assert result["access_token"] == "an-access-token"
    assert result["refresh_token"] == "a-raw-refresh-token"
    assert result["user"]["email"] == "driver@team.example"
    assert result["user"]["department"] == "sporting"


def test_login_creates_a_hashed_refresh_token_row():
    collaborators = _collaborators(user=_user())

    login("driver@team.example", "correct-password", **collaborators)

    collaborators["repository"].create_refresh_token.assert_called_once()
    args, _ = collaborators["repository"].create_refresh_token.call_args
    assert args[2] == "a-hashed-refresh-token"


def test_login_raises_generic_error_for_wrong_password():
    collaborators = _collaborators(user=_user())

    with pytest.raises(ValueError):
        login("driver@team.example", "wrong-password", **collaborators)


def test_login_raises_generic_error_for_unknown_email():
    collaborators = _collaborators(user=None)

    with pytest.raises(ValueError) as unknown_email_error:
        login("nobody@team.example", "correct-password", **collaborators)

    collaborators2 = _collaborators(user=_user())
    with pytest.raises(ValueError) as wrong_password_error:
        login("driver@team.example", "wrong-password", **collaborators2)

    assert str(unknown_email_error.value) == str(wrong_password_error.value)


def test_refresh_access_token_returns_new_access_token_and_rotates():
    collaborators = _collaborators(
        user=_user(), valid_refresh={"id": "rt-1", "user_id": "user-123", "expires_at": None}
    )

    result = refresh_access_token("a-raw-refresh-token", **collaborators)

    assert result["access_token"] == "an-access-token"
    assert result["refresh_token"] == "a-raw-refresh-token"
    collaborators["repository"].revoke_refresh_token.assert_called_once()
    collaborators["repository"].create_refresh_token.assert_called_once()


def test_refresh_access_token_raises_for_invalid_or_expired_token():
    collaborators = _collaborators(user=_user(), valid_refresh=None)

    with pytest.raises(ValueError):
        refresh_access_token("not-a-valid-refresh-token", **collaborators)

    collaborators["repository"].create_refresh_token.assert_not_called()


def test_logout_revokes_the_matching_refresh_token():
    collaborators = _collaborators()

    logout(
        "a-raw-refresh-token",
        conn=collaborators["conn"],
        repository=collaborators["repository"],
        security=collaborators["security"],
    )

    collaborators["security"].hash_token.assert_called_once_with("a-raw-refresh-token")
    collaborators["repository"].revoke_refresh_token.assert_called_once_with(
        collaborators["conn"], "a-hashed-refresh-token"
    )


def test_logout_is_a_no_op_when_no_refresh_token_provided():
    collaborators = _collaborators()

    logout(
        None,
        conn=collaborators["conn"],
        repository=collaborators["repository"],
        security=collaborators["security"],
    )

    collaborators["repository"].revoke_refresh_token.assert_not_called()


def test_register_creates_a_hashed_password_user_and_returns_a_session():
    created = _user(id="new-user-id", email="newdriver@team.example", department="technical")
    collaborators = _collaborators(user=None, created_user=created)

    result = register("newdriver@team.example", "a-password", "technical", **collaborators)

    collaborators["repository"].create_user.assert_called_once_with(
        collaborators["conn"], "newdriver@team.example", "a-hashed-password", "technical"
    )
    assert result["access_token"] == "an-access-token"
    assert result["user"]["email"] == "newdriver@team.example"
    assert result["user"]["department"] == "technical"


def test_register_rejects_a_duplicate_email_before_hashing_or_writing():
    collaborators = _collaborators(user=_user(email="existing@team.example"))

    with pytest.raises(ValueError):
        register("existing@team.example", "a-password", "sporting", **collaborators)

    collaborators["security"].hash_password.assert_not_called()
    collaborators["repository"].create_user.assert_not_called()


def test_register_rejects_an_empty_password_before_any_lookup_or_write():
    collaborators = _collaborators(user=None)

    with pytest.raises(ValueError):
        register("newdriver@team.example", "", "sporting", **collaborators)

    collaborators["repository"].get_user_by_email.assert_not_called()
    collaborators["security"].hash_password.assert_not_called()
    collaborators["repository"].create_user.assert_not_called()


def _event_record(caplog, event: str) -> logging.LogRecord:
    return next(r for r in caplog.records if getattr(r, "event", None) == event)


def test_login_logs_a_login_succeeded_event_with_email_and_user_id(caplog):
    caplog.set_level(logging.INFO)
    collaborators = _collaborators(user=_user())

    login("driver@team.example", "correct-password", **collaborators)

    record = _event_record(caplog, "login_succeeded")
    assert record.levelno == logging.INFO
    assert record.email == "driver@team.example"
    assert record.user_id == "user-123"


def test_login_logs_a_login_failed_event_on_wrong_password(caplog):
    caplog.set_level(logging.INFO)
    collaborators = _collaborators(user=_user())

    with pytest.raises(ValueError):
        login("driver@team.example", "wrong-password", **collaborators)

    record = _event_record(caplog, "login_failed")
    assert record.levelno == logging.WARNING
    assert record.email == "driver@team.example"
    assert record.user_id is None


def test_login_logs_a_login_failed_event_for_an_unknown_email(caplog):
    caplog.set_level(logging.INFO)
    collaborators = _collaborators(user=None)

    with pytest.raises(ValueError):
        login("nobody@team.example", "correct-password", **collaborators)

    record = _event_record(caplog, "login_failed")
    assert record.email == "nobody@team.example"
    assert record.user_id is None


def test_logout_looks_up_the_account_before_revoking_and_logs_logout_succeeded(caplog):
    caplog.set_level(logging.INFO)
    collaborators = _collaborators(
        valid_refresh={"id": "rt-1", "user_id": "user-123", "expires_at": None}
    )

    logout(
        "a-raw-refresh-token",
        conn=collaborators["conn"],
        repository=collaborators["repository"],
        security=collaborators["security"],
    )

    collaborators["repository"].get_valid_refresh_token.assert_called_once_with(
        collaborators["conn"], "a-hashed-refresh-token"
    )
    record = _event_record(caplog, "logout_succeeded")
    assert record.user_id == "user-123"


def test_logout_still_revokes_when_the_token_is_not_found_in_a_lookup(caplog):
    caplog.set_level(logging.INFO)
    collaborators = _collaborators(valid_refresh=None)

    logout(
        "a-raw-refresh-token",
        conn=collaborators["conn"],
        repository=collaborators["repository"],
        security=collaborators["security"],
    )

    collaborators["repository"].revoke_refresh_token.assert_called_once_with(
        collaborators["conn"], "a-hashed-refresh-token"
    )
    record = _event_record(caplog, "logout_succeeded")
    assert record.user_id is None


def test_register_logs_a_registration_succeeded_event(caplog):
    caplog.set_level(logging.INFO)
    created = _user(id="new-user-id", email="newdriver@team.example", department="technical")
    collaborators = _collaborators(user=None, created_user=created)

    register("newdriver@team.example", "a-password", "technical", **collaborators)

    record = _event_record(caplog, "registration_succeeded")
    assert record.email == "newdriver@team.example"
    assert record.user_id == "new-user-id"


def test_no_auth_log_record_ever_contains_a_password_value(caplog):
    caplog.set_level(logging.DEBUG)
    login_collaborators = _collaborators(user=_user())
    with pytest.raises(ValueError):
        # This mock's verify_password only accepts "correct-password" (see
        # _collaborators), so this login is expected to fail — the point
        # here is only that the attempted password never appears in a log.
        login("driver@team.example", "login-secret-pw", **login_collaborators)

    created = _user(id="new-user-id", email="newdriver@team.example")
    register_collaborators = _collaborators(user=None, created_user=created)
    register("newdriver@team.example", "register-secret-pw", "sporting", **register_collaborators)

    for record in caplog.records:
        dump = str(record.__dict__)
        assert "login-secret-pw" not in dump
        assert "register-secret-pw" not in dump

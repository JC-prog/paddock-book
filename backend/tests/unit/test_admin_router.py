from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.security import get_current_user
from src.main import app

client = TestClient(app)

_FAKE_ADMIN = {"sub": "admin-1", "email": "admin@team.example", "department": "sporting", "is_admin": True}
_FAKE_NON_ADMIN = {
    "sub": "user-1",
    "email": "driver@team.example",
    "department": "sporting",
    "is_admin": False,
}


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def _as_admin():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_ADMIN


def _as_non_admin():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_NON_ADMIN


def test_get_setting_rejects_unauthenticated_requests():
    response = client.get("/v1/admin/settings/log-destination")

    assert response.status_code == 401


def test_get_setting_rejects_a_non_admin():
    _as_non_admin()

    response = client.get("/v1/admin/settings/log-destination")

    assert response.status_code == 403


def test_get_setting_returns_the_current_value_for_an_admin():
    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch("src.modules.admin.router.get_log_destination", return_value=True),
    ):
        response = client.get("/v1/admin/settings/log-destination")

    assert response.status_code == 200
    assert response.json() == {"log_to_file": True}


def test_put_setting_updates_and_returns_the_new_value():
    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch("src.modules.admin.router.update_log_destination", return_value=False) as mock_update,
    ):
        response = client.put("/v1/admin/settings/log-destination", json={"log_to_file": False})

    assert response.status_code == 200
    assert response.json() == {"log_to_file": False}
    mock_update.assert_called_once()


def test_put_setting_rejects_a_non_admin():
    _as_non_admin()

    response = client.put("/v1/admin/settings/log-destination", json={"log_to_file": False})

    assert response.status_code == 403


def test_put_setting_rejects_a_missing_body_field():
    _as_admin()

    response = client.put("/v1/admin/settings/log-destination", json={})

    assert response.status_code == 422


def test_put_setting_rejects_a_non_boolean_value():
    _as_admin()

    response = client.put("/v1/admin/settings/log-destination", json={"log_to_file": "yes"})

    assert response.status_code == 422


_FAKE_CHAT_PROVIDER_CONFIG = {
    "active_provider": "ollama",
    "ollama_model_override": None,
    "bedrock_model": None,
    "openai_compatible_base_url": None,
    "openai_compatible_model": None,
    "openai_compatible_api_key_set": False,
}


def test_get_chat_provider_rejects_unauthenticated_requests():
    response = client.get("/v1/admin/settings/chat-provider")

    assert response.status_code == 401


def test_get_chat_provider_rejects_a_non_admin():
    _as_non_admin()

    response = client.get("/v1/admin/settings/chat-provider")

    assert response.status_code == 403


def test_get_chat_provider_returns_the_current_config_for_an_admin():
    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch(
            "src.modules.admin.router.get_chat_provider_config",
            return_value=_FAKE_CHAT_PROVIDER_CONFIG,
        ),
    ):
        response = client.get("/v1/admin/settings/chat-provider")

    assert response.status_code == 200
    assert response.json() == _FAKE_CHAT_PROVIDER_CONFIG


def test_put_chat_provider_rejects_a_non_admin():
    _as_non_admin()

    response = client.put("/v1/admin/settings/chat-provider", json={"active_provider": "ollama"})

    assert response.status_code == 403


def test_put_chat_provider_updates_and_returns_the_new_config():
    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch(
            "src.modules.admin.router.update_chat_provider_config",
            return_value=_FAKE_CHAT_PROVIDER_CONFIG,
        ) as mock_update,
    ):
        response = client.put("/v1/admin/settings/chat-provider", json={"active_provider": "ollama"})

    assert response.status_code == 200
    assert response.json() == _FAKE_CHAT_PROVIDER_CONFIG
    mock_update.assert_called_once()


def test_put_chat_provider_only_forwards_fields_present_in_the_request_body():
    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch(
            "src.modules.admin.router.update_chat_provider_config",
            return_value=_FAKE_CHAT_PROVIDER_CONFIG,
        ) as mock_update,
    ):
        client.put("/v1/admin/settings/chat-provider", json={"active_provider": "bedrock"})

    args, kwargs = mock_update.call_args
    updates = args[0] if args else kwargs["updates"]
    assert updates == {"active_provider": "bedrock"}


def test_put_chat_provider_rejects_an_unknown_provider_value():
    _as_admin()

    response = client.put("/v1/admin/settings/chat-provider", json={"active_provider": "not-a-real-provider"})

    assert response.status_code == 422


def test_put_chat_provider_maps_incomplete_provider_config_to_409():
    from src.modules.admin.service import IncompleteProviderConfigError

    _as_admin()

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch(
            "src.modules.admin.router.update_chat_provider_config",
            side_effect=IncompleteProviderConfigError("bedrock requires a model identifier"),
        ),
    ):
        response = client.put("/v1/admin/settings/chat-provider", json={"active_provider": "bedrock"})

    assert response.status_code == 409
    assert "bedrock requires a model identifier" in response.json()["detail"]


def test_put_chat_provider_returns_409_for_a_real_missing_bedrock_model(monkeypatch):
    # No mocking of update_chat_provider_config here — exercises the real
    # service function (with a mocked repository injected through the
    # real function's own DI kwarg default, not module patching, since
    # default parameter values are bound at definition time) to confirm
    # the router's 409 mapping fires end-to-end for the concrete Bedrock
    # case, not just against a hand-raised exception (T012's generic test).
    import src.modules.admin.router as router_module
    from src.modules.admin import repository as real_repository
    from src.modules.admin.service import update_chat_provider_config

    _as_admin()
    fake_repository = MagicMock(spec=real_repository)
    fake_repository.get_chat_provider_settings.return_value = None

    def _real_update_with_fake_repository(updates, *, conn, admin_user):
        return update_chat_provider_config(updates, conn=conn, admin_user=admin_user, repository=fake_repository)

    with (
        patch("src.modules.admin.router.get_connection", MagicMock()),
        patch.object(router_module, "update_chat_provider_config", _real_update_with_fake_repository),
    ):
        response = client.put("/v1/admin/settings/chat-provider", json={"active_provider": "bedrock"})

    assert response.status_code == 409
    assert "bedrock" in response.json()["detail"]

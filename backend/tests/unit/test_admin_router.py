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

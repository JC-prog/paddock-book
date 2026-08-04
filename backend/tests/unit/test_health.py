import time

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_returns_200_ok_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_requires_no_authentication():
    response = client.get("/health")

    assert response.status_code != 401
    assert response.status_code != 403


def test_health_responds_within_500ms():
    start = time.monotonic()
    response = client.get("/health")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 500

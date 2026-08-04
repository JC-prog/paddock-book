from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_cors_preflight_allows_post_to_chat_from_frontend_origin():
    response = client.options(
        "/v1/chat",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert "POST" in response.headers["access-control-allow-methods"]

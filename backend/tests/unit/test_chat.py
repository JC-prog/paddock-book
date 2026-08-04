import pytest
from fastapi.testclient import TestClient
from sse_starlette.sse import AppStatus

from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_sse_starlette_app_status():
    # sse-starlette's AppStatus.should_exit_event binds to whichever event
    # loop first creates it; TestClient.stream() spins up a fresh event loop
    # per call, so it must be reset between tests to avoid a stale-loop error.
    AppStatus.should_exit_event = None
    yield


def _data_events(response) -> list[str]:
    events: list[str] = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            events.append(line[len("data:"):].strip())
    return events


def test_chat_streams_placeholder_as_multiple_discrete_events():
    with client.stream("POST", "/v1/chat", json={"message": "hi"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _data_events(response)

    assert len(events) > 1
    assert " ".join(events) == "Hello, this is a test response."


def test_chat_rejects_empty_message():
    response = client.post("/v1/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_message():
    response = client.post("/v1/chat", json={"message": "   "})

    assert response.status_code == 422


def test_chat_does_not_raise_on_early_client_disconnect():
    with client.stream("POST", "/v1/chat", json={"message": "hi"}) as response:
        assert response.status_code == 200
        next(response.iter_lines())
        # Exiting the `with` block here closes the connection mid-stream;
        # the assertion is simply that doing so raises nothing.

import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sse_starlette.sse import AppStatus

from src.core.security import get_current_user
from src.main import app

client = TestClient(app)

_FAKE_USER = {"sub": "user-123", "email": "driver@team.example", "department": "sporting"}
_FAKE_CHUNKS = [{"document_title": "Sporting Regs", "chunk_text": "Cars must have four wheels."}]


@pytest.fixture(autouse=True)
def _reset_sse_starlette_app_status():
    # sse-starlette's AppStatus.should_exit_event binds to whichever event
    # loop first creates it; TestClient.stream() spins up a fresh event loop
    # per call, so it must be reset between tests to avoid a stale-loop error.
    AppStatus.should_exit_event = None
    yield


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def _data_events(response) -> list[str]:
    events: list[str] = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            events.append(line[len("data:"):].strip())
    return events


def _authenticated():
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER


def _fake_retrieve_context(message, department, *, conn):
    assert department == "sporting"
    return _FAKE_CHUNKS


async def _fake_generate_reply(message, chunks):
    assert chunks == _FAKE_CHUNKS
    yield "Real"
    yield "answer"


def test_chat_rejects_unauthenticated_requests():
    response = client.post("/v1/chat", json={"message": "hi"})

    assert response.status_code == 401


def test_chat_rejects_empty_message_even_when_authenticated():
    _authenticated()

    with patch("src.modules.chat.router.get_connection", MagicMock()):
        response = client.post("/v1/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_message_even_when_authenticated():
    _authenticated()

    with patch("src.modules.chat.router.get_connection", MagicMock()):
        response = client.post("/v1/chat", json={"message": "   "})

    assert response.status_code == 422


def test_chat_streams_the_generated_reply_for_an_authenticated_request():
    _authenticated()

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _fake_retrieve_context),
        patch("src.modules.chat.router.generate_reply", _fake_generate_reply),
    ):
        with client.stream("POST", "/v1/chat", json={"message": "hi"}) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            events = _data_events(response)

    assert events == ["Real", "answer"]


def test_chat_returns_a_clean_error_without_opening_a_stream_when_retrieval_fails():
    _authenticated()

    def _failing_retrieve_context(message, department, *, conn):
        raise RuntimeError("Bedrock embedding call failed: Unable to locate credentials")

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _failing_retrieve_context),
    ):
        response = client.post("/v1/chat", json={"message": "hi"})

    assert response.status_code == 502
    assert not response.headers["content-type"].startswith("text/event-stream")


def test_chat_does_not_raise_on_early_client_disconnect():
    _authenticated()

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _fake_retrieve_context),
        patch("src.modules.chat.router.generate_reply", _fake_generate_reply),
    ):
        with client.stream("POST", "/v1/chat", json={"message": "hi"}) as response:
            assert response.status_code == 200
            next(response.iter_lines())
            # Exiting the `with` block here closes the connection mid-stream;
            # the assertion is simply that doing so raises nothing.


def test_chat_logs_a_chat_retrieval_succeeded_event_with_account_and_department(caplog):
    caplog.set_level(logging.INFO)
    _authenticated()

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _fake_retrieve_context),
        patch("src.modules.chat.router.generate_reply", _fake_generate_reply),
    ):
        with client.stream("POST", "/v1/chat", json={"message": "hi"}) as response:
            list(response.iter_lines())

    record = next(r for r in caplog.records if getattr(r, "event", None) == "chat_retrieval_succeeded")
    assert record.user_id == "user-123"
    assert record.departments == ["sporting"]


def test_chat_event_log_does_not_contain_the_question_text(caplog):
    caplog.set_level(logging.DEBUG)
    _authenticated()
    unique_question = "zzz-unique-test-question-xyz123"

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _fake_retrieve_context),
        patch("src.modules.chat.router.generate_reply", _fake_generate_reply),
    ):
        with client.stream("POST", "/v1/chat", json={"message": unique_question}) as response:
            list(response.iter_lines())

    for record in caplog.records:
        assert unique_question not in str(record.__dict__)


def test_chat_event_log_not_produced_when_retrieval_fails(caplog):
    caplog.set_level(logging.INFO)
    _authenticated()

    def _failing_retrieve_context(message, department, *, conn):
        raise RuntimeError("boom")

    with (
        patch("src.modules.chat.router.get_connection", MagicMock()),
        patch("src.modules.chat.router.retrieve_context", _failing_retrieve_context),
    ):
        client.post("/v1/chat", json={"message": "hi"})

    assert not any(getattr(r, "event", None) == "chat_retrieval_succeeded" for r in caplog.records)

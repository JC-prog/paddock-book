import asyncio
import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging import configure_logging, request_id_var
from src.core.middleware import RequestLoggingMiddleware

pytestmark = pytest.mark.anyio


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ok")
    def ok():
        return {"status": "ok"}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def _make_request(path: str) -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": []})


@pytest.fixture(autouse=True)
def _reset_root_logger():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)


def _log_lines(capsys) -> list[dict]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.strip().splitlines() if line]


def test_successful_request_logs_method_path_status_and_duration(capsys):
    configure_logging()
    client = TestClient(_build_app())

    response = client.get("/ok")

    assert response.status_code == 200
    entry = next(e for e in _log_lines(capsys) if e.get("path") == "/ok")
    assert entry["method"] == "GET"
    assert entry["status_code"] == 200
    assert entry["duration_ms"] >= 0
    assert entry["level"] == "INFO"
    assert entry["request_id"]


def test_unhandled_exception_logs_error_and_still_produces_a_500(capsys):
    configure_logging()
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    entry = next(e for e in _log_lines(capsys) if e.get("path") == "/boom")
    assert entry["level"] == "ERROR"
    assert entry["status_code"] is None
    assert "RuntimeError" in entry["exc_info"]
    assert "kaboom" in entry["exc_info"]


async def test_a_logging_handler_failure_does_not_fail_the_request():
    # Deliberately calls dispatch() directly (not via TestClient) so only
    # this middleware's own logging is exercised — TestClient's underlying
    # httpx client does its own independent logging via the same root
    # logger, which would otherwise confound this test with a failure
    # that has nothing to do with this middleware's own FR-007 guarantee.
    configure_logging()
    for handler in logging.getLogger().handlers:
        handler.emit = MagicMock(side_effect=RuntimeError("disk full"))

    middleware = RequestLoggingMiddleware(app=None)

    async def call_next(request: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(_make_request("/ok"), call_next)

    assert response.status_code == 200


async def test_concurrent_requests_do_not_leak_request_ids_into_each_other():
    middleware = RequestLoggingMiddleware(app=None)
    seen_ids: dict[str, str | None] = {}

    async def call_next(request: Request) -> Response:
        await asyncio.sleep(0.01)
        seen_ids[request.url.path] = request_id_var.get()
        return Response(status_code=200)

    await asyncio.gather(
        middleware.dispatch(_make_request("/a"), call_next),
        middleware.dispatch(_make_request("/b"), call_next),
    )

    assert seen_ids["/a"] is not None
    assert seen_ids["/b"] is not None
    assert seen_ids["/a"] != seen_ids["/b"]

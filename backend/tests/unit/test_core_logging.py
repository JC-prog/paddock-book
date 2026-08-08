import json
import logging

import pytest

from src.core.logging import JsonFormatter, configure_logging, request_id_var


def _make_record(msg="hello", level=logging.INFO, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="src.test", level=level, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_produces_the_common_envelope_fields():
    record = _make_record("something happened")

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "something happened"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "src.test"
    assert "timestamp" in payload
    assert payload["request_id"] is None


def test_json_formatter_includes_the_current_request_id_when_set():
    token = request_id_var.set("abc-123")
    try:
        record = _make_record("during a request")
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert payload["request_id"] == "abc-123"


def test_json_formatter_merges_extra_fields():
    record = _make_record("chat retrieval succeeded", event="chat_retrieval_succeeded", user_id="u1")

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "chat_retrieval_succeeded"
    assert payload["user_id"] == "u1"


def test_json_formatter_includes_formatted_exception_info_when_present():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _make_record("unhandled exception", level=logging.ERROR, exc_info=sys.exc_info())

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in payload["exc_info"]


def test_json_formatter_omits_exc_info_key_when_no_exception():
    record = _make_record("plain message")

    payload = json.loads(JsonFormatter().format(record))

    assert "exc_info" not in payload


@pytest.fixture(autouse=True)
def _reset_root_logger():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)


def test_configure_logging_attaches_a_json_formatting_handler_to_the_root_logger():
    configure_logging()

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)


def test_configure_logging_output_includes_the_current_request_id(capsys):
    configure_logging()
    token = request_id_var.set("req-42")
    try:
        logging.getLogger("src.test").info("hi")
    finally:
        request_id_var.reset(token)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["request_id"] == "req-42"

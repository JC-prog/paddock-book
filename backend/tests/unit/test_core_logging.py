import json
import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock

import pytest

from src.core.logging import JsonFormatter, configure_logging, request_id_var


def _fake_settings(**overrides):
    defaults = dict(
        log_to_file=False,
        log_file_path="logs/app.log",
        log_file_max_bytes=10 * 1024 * 1024,
        log_file_backup_count=5,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


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
    configure_logging(settings_factory=_fake_settings)

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)


def test_configure_logging_output_includes_the_current_request_id(capsys):
    configure_logging(settings_factory=_fake_settings)
    token = request_id_var.set("req-42")
    try:
        logging.getLogger("src.test").info("hi")
    finally:
        request_id_var.reset(token)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["request_id"] == "req-42"


def test_configure_logging_attaches_a_rotating_file_handler_when_enabled(tmp_path):
    log_path = tmp_path / "app.log"
    settings = _fake_settings(log_to_file=True, log_file_path=str(log_path), log_file_max_bytes=1024, log_file_backup_count=3)

    configure_logging(settings_factory=lambda: settings)

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(file_handlers) == 1
    handler = file_handlers[0]
    assert handler.maxBytes == 1024
    assert handler.backupCount == 3
    assert isinstance(handler.formatter, JsonFormatter)


def test_configure_logging_writes_a_real_json_line_to_the_file(tmp_path):
    log_path = tmp_path / "app.log"
    settings = _fake_settings(log_to_file=True, log_file_path=str(log_path))

    configure_logging(settings_factory=lambda: settings)
    logging.getLogger("src.test").info("hello file")

    content = log_path.read_text()
    payload = json.loads(content.strip().splitlines()[-1])
    assert payload["message"] == "hello file"


def test_configure_logging_does_not_attach_a_file_handler_when_disabled(tmp_path):
    log_path = tmp_path / "app.log"
    settings = _fake_settings(log_to_file=False, log_file_path=str(log_path))

    configure_logging(settings_factory=lambda: settings)

    root = logging.getLogger()
    assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    assert not log_path.exists()


def test_configure_logging_creates_the_log_directory_if_missing(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "app.log"
    settings = _fake_settings(log_to_file=True, log_file_path=str(log_path))

    configure_logging(settings_factory=lambda: settings)

    assert log_path.parent.exists()


def test_configure_logging_falls_back_to_stdout_only_when_the_file_destination_is_unwritable(tmp_path, capsys):
    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("i am a file, not a directory")
    log_path = blocking_file / "app.log"
    settings = _fake_settings(log_to_file=True, log_file_path=str(log_path))

    configure_logging(settings_factory=lambda: settings)

    root = logging.getLogger()
    assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    lines = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines() if line]
    warning = next(line for line in lines if line.get("event") == "log_file_setup_failed")
    assert warning["level"] == "WARNING"


def test_configure_logging_falls_back_to_stdout_only_when_settings_cannot_be_read(capsys):
    # Regression check: configure_logging() is called at import time in
    # main.py, with no env vars guaranteed to be set (e.g. real CI, which
    # has no .env file at all) — a settings_factory that raises (missing
    # required fields unrelated to logging, etc.) must not prevent the
    # app from starting, matching FR-005's intent broadly, not just for
    # file-handler construction specifically.
    def _broken_settings_factory():
        raise RuntimeError("missing required settings")

    configure_logging(settings_factory=_broken_settings_factory)

    root = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)

    lines = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines() if line]
    warning = next(line for line in lines if line.get("event") == "log_file_setup_failed")
    assert warning["level"] == "WARNING"


def test_configure_logging_rolls_the_file_over_once_it_exceeds_max_bytes(tmp_path):
    log_path = tmp_path / "app.log"
    settings = _fake_settings(
        log_to_file=True, log_file_path=str(log_path), log_file_max_bytes=200, log_file_backup_count=3
    )

    configure_logging(settings_factory=lambda: settings)
    test_logger = logging.getLogger("src.test.rotation_a")
    for i in range(50):
        test_logger.info(f"log entry number {i} with some padding text to grow the file")

    assert log_path.exists()
    assert (tmp_path / "app.log.1").exists()


def test_configure_logging_never_keeps_more_files_than_backup_count_plus_one(tmp_path):
    log_path = tmp_path / "app.log"
    backup_count = 2
    settings = _fake_settings(
        log_to_file=True,
        log_file_path=str(log_path),
        log_file_max_bytes=100,
        log_file_backup_count=backup_count,
    )

    configure_logging(settings_factory=lambda: settings)
    test_logger = logging.getLogger("src.test.rotation_b")
    for i in range(300):
        test_logger.info(f"log entry number {i} with padding text to force many rotations")

    all_log_files = list(tmp_path.glob("app.log*"))
    assert len(all_log_files) <= backup_count + 1


def test_configure_logging_caps_total_disk_usage_across_many_rotations(tmp_path):
    log_path = tmp_path / "app.log"
    max_bytes = 500
    backup_count = 3
    settings = _fake_settings(
        log_to_file=True,
        log_file_path=str(log_path),
        log_file_max_bytes=max_bytes,
        log_file_backup_count=backup_count,
    )

    configure_logging(settings_factory=lambda: settings)
    test_logger = logging.getLogger("src.test.rotation_c")
    for i in range(500):
        test_logger.info(f"log entry number {i} with enough padding text to grow files at a steady rate")

    all_log_files = list(tmp_path.glob("app.log*"))
    total_size = sum(f.stat().st_size for f in all_log_files)
    # RotatingFileHandler only checks size *before* writing the next record, so
    # a file can overshoot max_bytes by up to roughly one record's worth right
    # before it rolls over — allow one extra file's worth of slack for that,
    # not unbounded growth.
    assert total_size <= max_bytes * (backup_count + 2)

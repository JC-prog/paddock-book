import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.core.config import Settings

logger = logging.getLogger(__name__)

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
    "request_id",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def _try_build_file_handler(path: str, max_bytes: int, backup_count: int) -> RotatingFileHandler | None:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
    except OSError:
        return None

    handler.setFormatter(JsonFormatter())
    return handler


def configure_logging(level: int = logging.INFO, *, settings_factory=Settings) -> None:
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [stdout_handler]
    root.setLevel(level)

    try:
        settings = settings_factory()
    except Exception:
        # configure_logging() runs at import time (main.py), before any
        # env vars are guaranteed available (e.g. CI has no .env file at
        # all) — a settings read failing here must degrade to stdout-only
        # rather than crash app startup, matching FR-005's intent broadly.
        logger.warning(
            "could not read settings for log file configuration; continuing with stdout only",
            extra={"event": "log_file_setup_failed"},
        )
        return

    if settings.log_to_file:
        file_handler = _try_build_file_handler(
            settings.log_file_path, settings.log_file_max_bytes, settings.log_file_backup_count
        )
        if file_handler is not None:
            root.addHandler(file_handler)
        else:
            logger.warning(
                "log file handler could not be configured; continuing with stdout only",
                extra={"event": "log_file_setup_failed", "log_file_path": settings.log_file_path},
            )

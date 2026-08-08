import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging import request_id_var

logger = logging.getLogger(__name__)


def _log_safely(log_call) -> None:
    # Handler.handle() has no try/except of its own around emit() — only
    # StreamHandler.emit()'s own body (write/flush) is self-protected via
    # handleError(). A handler failing more fundamentally than that would
    # otherwise propagate straight into request handling, violating FR-007.
    try:
        log_call()
    except Exception:
        pass


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        token = request_id_var.set(str(uuid.uuid4()))
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            _log_safely(
                lambda: logger.error(
                    "unhandled exception",
                    exc_info=True,
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": None,
                        "duration_ms": duration_ms,
                    },
                )
            )
            raise
        else:
            duration_ms = (time.monotonic() - start) * 1000
            _log_safely(
                lambda: logger.info(
                    "request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            )
            return response
        finally:
            request_id_var.reset(token)

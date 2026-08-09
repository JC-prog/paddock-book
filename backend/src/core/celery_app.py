import logging

from celery import Celery

from src.core.config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_BROKER_URL = "redis://localhost:6380/0"


def _build_celery_app(*, settings_factory=Settings) -> Celery:
    try:
        redis_url = settings_factory().redis_url
    except Exception:
        # core/celery_app.py is imported at backend startup (main.py, to
        # enqueue tasks) before any env vars are guaranteed available
        # (e.g. real CI has no .env at all) — a settings read failing
        # here must not prevent import, matching the graceful-degradation
        # pattern configure_logging() already established (features
        # 010-012).
        logger.warning(
            "could not read settings for the task queue; falling back to the default broker URL",
            extra={"event": "celery_app_settings_fallback"},
        )
        redis_url = _DEFAULT_BROKER_URL

    return Celery(
        "paddockbook",
        broker=redis_url,
        backend=redis_url,
        include=["src.modules.jobs.tasks"],
    )


celery_app = _build_celery_app()

from src.core.logging import configure_logging

configure_logging()

from src.core.celery_app import celery_app  # noqa: E402

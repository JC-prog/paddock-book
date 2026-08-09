from unittest.mock import MagicMock

from src.core.celery_app import _build_celery_app


def test_build_celery_app_uses_settings_redis_url_when_available():
    settings_factory = MagicMock(return_value=MagicMock(redis_url="redis://redis.internal:6379/0"))

    app = _build_celery_app(settings_factory=settings_factory)

    assert app.conf.broker_url == "redis://redis.internal:6379/0"
    assert app.conf.result_backend == "redis://redis.internal:6379/0"


def test_build_celery_app_falls_back_to_a_default_url_when_settings_cannot_be_read():
    # configure_logging() (features 010-012) already established this
    # regression class: this module is imported at backend startup
    # (main.py, to enqueue tasks), before any env vars are guaranteed
    # available (e.g. real CI has no .env at all) — a settings read
    # failing here must not prevent import, matching that established
    # graceful-degradation pattern.
    def _broken_settings_factory():
        raise RuntimeError("missing required settings")

    app = _build_celery_app(settings_factory=_broken_settings_factory)

    assert app.conf.broker_url is not None
    assert app.conf.result_backend is not None

import pytest
from pydantic import ValidationError

from src.core.config import Settings


@pytest.fixture(autouse=True)
def _default_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")


def test_settings_reads_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

    settings = Settings()

    assert settings.database_url == "postgresql://user:pass@localhost:5432/db"


def test_settings_defaults_aws_region_when_not_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.delenv("AWS_REGION", raising=False)

    settings = Settings()

    assert settings.aws_region == "us-east-1"


def test_settings_reads_aws_region_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")

    settings = Settings()

    assert settings.aws_region == "eu-west-2"


def test_settings_raises_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_raises_when_jwt_secret_missing(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reads_jwt_secret_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "a-signing-secret")

    settings = Settings()

    assert settings.jwt_secret == "a-signing-secret"


def test_settings_defaults_access_token_ttl_minutes_when_not_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.delenv("ACCESS_TOKEN_TTL_MINUTES", raising=False)

    settings = Settings()

    assert settings.access_token_ttl_minutes == 15


def test_settings_reads_access_token_ttl_minutes_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_MINUTES", "30")

    settings = Settings()

    assert settings.access_token_ttl_minutes == 30


def test_settings_defaults_refresh_token_ttl_days_when_not_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.delenv("REFRESH_TOKEN_TTL_DAYS", raising=False)

    settings = Settings()

    assert settings.refresh_token_ttl_days == 7


def test_settings_reads_refresh_token_ttl_days_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("REFRESH_TOKEN_TTL_DAYS", "14")

    settings = Settings()

    assert settings.refresh_token_ttl_days == 14


def test_settings_defaults_cookie_secure_to_false_when_not_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)

    settings = Settings()

    # False by default so the refresh cookie still round-trips over plain
    # http://localhost in local dev — a Secure cookie is silently dropped by
    # the browser (and by httpx's TestClient) over a non-HTTPS connection.
    assert settings.cookie_secure is False


def test_settings_reads_cookie_secure_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    settings = Settings()

    assert settings.cookie_secure is True

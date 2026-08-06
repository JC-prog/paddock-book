import pytest
from pydantic import ValidationError

from src.core.config import Settings


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

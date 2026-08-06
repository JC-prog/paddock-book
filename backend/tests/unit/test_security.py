from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src.core.config import Settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    verify_password,
)


def _settings(**overrides) -> Settings:
    defaults = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "jwt_secret": "test-secret",
        "access_token_ttl_minutes": 15,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_hash_password_produces_a_verifiable_hash():
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed) is True


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("correct horse battery staple")

    assert hashed != "correct horse battery staple"


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")

    assert verify_password("wrong password", hashed) is False


def test_create_and_decode_access_token_round_trips_claims():
    settings = _settings()

    token = create_access_token(
        sub="user-123", email="driver@team.example", department="sporting", settings=settings
    )
    claims = decode_access_token(token, settings)

    assert claims == {"sub": "user-123", "email": "driver@team.example", "department": "sporting"}


def test_decode_access_token_raises_for_tampered_token():
    settings = _settings()
    token = create_access_token(sub="user-123", email="a@b.com", department="sporting", settings=settings)
    # Replace the last few characters of the signature rather than just one —
    # a single-character base64url flip can land on a bit boundary that
    # doesn't actually change the decoded signature bytes, making the
    # tampered token spuriously still valid.
    tampered = token[:-4] + ("abcd" if not token.endswith("abcd") else "wxyz")

    with pytest.raises(ValueError):
        decode_access_token(tampered, settings)


def test_decode_access_token_raises_for_expired_token():
    settings = _settings(access_token_ttl_minutes=-1)
    token = create_access_token(sub="user-123", email="a@b.com", department="sporting", settings=settings)

    with pytest.raises(ValueError):
        decode_access_token(token, settings)


def test_get_current_user_returns_claims_for_valid_bearer_header():
    settings = _settings()
    token = create_access_token(
        sub="user-123", email="driver@team.example", department="technical", settings=settings
    )

    claims = get_current_user(authorization=f"Bearer {token}", settings=settings)

    assert claims == {"sub": "user-123", "email": "driver@team.example", "department": "technical"}


def test_get_current_user_raises_401_for_missing_header():
    settings = _settings()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None, settings=settings)

    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_for_malformed_header():
    settings = _settings()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="not-a-bearer-token", settings=settings)

    assert exc_info.value.status_code == 401


def test_get_current_user_raises_401_for_invalid_token():
    settings = _settings()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="Bearer not-a-real-token", settings=settings)

    assert exc_info.value.status_code == 401


def test_generate_refresh_token_produces_a_high_entropy_unique_value():
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(first) >= 32


def test_hash_token_is_deterministic_and_does_not_return_the_raw_token():
    token = generate_refresh_token()

    hashed_once = hash_token(token)
    hashed_again = hash_token(token)

    assert hashed_once == hashed_again
    assert hashed_once != token

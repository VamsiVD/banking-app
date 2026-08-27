"""Tests for the access-token half of app/core/security.py.

Mostly about the verifier: that a token which should not be accepted is refused,
and refused as an app error rather than a stray library exception.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.errors import AppError, InvalidToken

USER_ID = "sam@example.com"


def _claims(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    claims = {"sub": USER_ID, "iat": now, "exp": now + timedelta(minutes=30)}
    claims.update(overrides)
    return claims


def test_a_token_round_trips_back_to_the_user_id():
    assert decode_access_token(create_access_token(USER_ID)) == USER_ID


def test_the_lifetime_comes_from_the_configured_expiry():
    payload = jwt.decode(create_access_token(USER_ID), options={"verify_signature": False})

    assert payload["exp"] - payload["iat"] == get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_an_explicit_zero_expiry_is_not_mistaken_for_no_argument():
    """Why the fallback tests `is None`: `or` would turn a deliberate 0 into 30."""
    payload = jwt.decode(
        create_access_token(USER_ID, expires_minutes=0), options={"verify_signature": False}
    )

    assert payload["exp"] == payload["iat"]


def test_an_expired_token_is_rejected():
    with pytest.raises(InvalidToken):
        decode_access_token(create_access_token(USER_ID, expires_minutes=-1))


def test_a_tampered_token_is_rejected():
    token = create_access_token(USER_ID)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(InvalidToken):
        decode_access_token(tampered)


def test_a_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(_claims(), "another-service-secret-that-is-long-enough", algorithm="HS256")

    with pytest.raises(InvalidToken):
        decode_access_token(forged)


def test_an_unsigned_token_is_rejected():
    """Fails if decode() loses its `algorithms=[...]` allow-list."""
    unsigned = jwt.encode(_claims(), key="", algorithm="none")

    with pytest.raises(InvalidToken):
        decode_access_token(unsigned)


def test_a_token_without_an_expiry_is_rejected():
    """Fails if decode() loses `options={"require": [...]}`."""
    claims = _claims()
    del claims["exp"]
    forever = jwt.encode(claims, get_settings().JWT_SECRET_KEY, algorithm="HS256")

    with pytest.raises(InvalidToken):
        decode_access_token(forever)


def test_a_token_without_a_subject_is_rejected():
    claims = _claims()
    del claims["sub"]
    anonymous = jwt.encode(claims, get_settings().JWT_SECRET_KEY, algorithm="HS256")

    with pytest.raises(InvalidToken):
        decode_access_token(anonymous)


def test_garbage_is_rejected_as_an_app_error_not_a_library_one():
    """An AppError subclass is what gets a 401 envelope instead of a 500."""
    with pytest.raises(InvalidToken) as caught:
        decode_access_token("this-is-not-a-token")

    assert isinstance(caught.value, AppError)
    assert caught.value.status_code == 401
    assert caught.value.code == "invalid_token"


def test_the_payload_is_readable_without_the_secret():
    """A JWT is signed, not encrypted — hence nothing sensitive goes in one."""
    token = create_access_token(USER_ID)

    assert jwt.decode(token, options={"verify_signature": False})["sub"] == USER_ID

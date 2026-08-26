"""Tests for the access-token half of app/core/security.py.

These are about the verifier, not the encoder. Minting a token that works is the
easy half; the half worth testing is that a token which *should not* be accepted
is refused, and refused as an app error rather than a stray library exception.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.errors import AppError, InvalidToken

USER_ID = "sam@example.com"


def _claims(**overrides) -> dict:
    """A payload shaped like a real one, so tests can vary a single field."""
    now = datetime.now(timezone.utc)
    claims = {"sub": USER_ID, "iat": now, "exp": now + timedelta(minutes=30)}
    claims.update(overrides)
    return claims


def test_a_token_round_trips_back_to_the_user_id():
    assert decode_access_token(create_access_token(USER_ID)) == USER_ID


def test_the_lifetime_comes_from_the_configured_expiry():
    token = create_access_token(USER_ID)
    payload = jwt.decode(token, options={"verify_signature": False})

    expected = get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert payload["exp"] - payload["iat"] == expected


def test_an_explicit_zero_expiry_is_not_mistaken_for_no_argument():
    """The reason the fallback tests `is None` and not truthiness.

    `expires_minutes or DEFAULT` would turn a deliberate 0 into 30 minutes, and
    the expiry test below would then be passing for the wrong reason.
    """
    payload = jwt.decode(
        create_access_token(USER_ID, expires_minutes=0), options={"verify_signature": False}
    )
    assert payload["exp"] == payload["iat"]


def test_an_expired_token_is_rejected():
    expired = create_access_token(USER_ID, expires_minutes=-1)

    with pytest.raises(InvalidToken):
        decode_access_token(expired)


def test_a_tampered_token_is_rejected():
    """Flip one character of the signature. The payload still parses; the
    signature no longer matches it, which is the entire point of signing."""
    token = create_access_token(USER_ID)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(InvalidToken):
        decode_access_token(tampered)


def test_a_token_signed_with_another_secret_is_rejected():
    """A well-formed, unexpired, correctly-shaped token that we did not issue."""
    forged = jwt.encode(_claims(), "another-service-secret-that-is-long-enough", algorithm="HS256")

    with pytest.raises(InvalidToken):
        decode_access_token(forged)


def test_an_unsigned_token_is_rejected():
    """The `alg: none` attack, which is why decode() gets an explicit
    `algorithms=[...]` allow-list. Without it this token would verify."""
    unsigned = jwt.encode(_claims(), key="", algorithm="none")

    with pytest.raises(InvalidToken):
        decode_access_token(unsigned)


def test_a_token_without_an_expiry_is_rejected():
    """A token with no `exp` never expires. Hence options={"require": [...]}."""
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
    """The guard depends on this: every failure arrives as an AppError subclass,
    so the handler in errors.py turns it into a 401 in the standard envelope
    instead of an unhandled 500."""
    with pytest.raises(InvalidToken) as caught:
        decode_access_token("this-is-not-a-token")

    assert isinstance(caught.value, AppError)
    assert caught.value.status_code == 401
    assert caught.value.code == "invalid_token"


def test_the_payload_is_readable_without_the_secret():
    """Not a bug — a JWT is signed, not encrypted. This test exists to record
    that we know it, and it is why nothing sensitive goes into a token."""
    token = create_access_token(USER_ID)

    assert jwt.decode(token, options={"verify_signature": False})["sub"] == USER_ID

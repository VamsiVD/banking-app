"""Credentials: password hashing, and the access tokens that stand in for a login.

Two jobs, kept in one file because they are the only places in the app that touch
a secret directly.

Worth being clear about what a JWT is not: it is *signed*, not encrypted. Anyone
holding a token can read every claim inside it without the key — the signature
proves the claims were not altered, it does not hide them. That is why a token
here carries a user id and two timestamps and nothing else. No password hash, no
balance, nothing that would be a problem to read aloud.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
# The PyJWT package. Note the mismatch: `pip install PyJWT`, `import jwt`.
# There is an unrelated package actually named `jwt`; installing it by mistake
# gives you a module with the same import name and a different API.
import jwt

from app.config import get_settings
from app.errors import InvalidToken

# Helper for auth_service

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


# Token generation and verification

def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    """Mint a signed token that says "this request is user_id, until exp"."""
    # Read settings here rather than at import time. get_settings() is cached, so
    # this costs nothing after the first call, and binding the values at import
    # would freeze them before load_dotenv() has necessarily run.
    settings = get_settings()

    # `is None`, not `or`: a caller asking for 0 minutes wants a token that is
    # already expired, and `0 or 30` would quietly hand them half an hour.
    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    # One timestamp used twice, so exp - iat is exactly the configured lifetime.
    # datetime.utcnow() is deprecated in 3.12 and returns a naive datetime that
    # gets read as local time; this one is unambiguous.
    now = datetime.now(timezone.utc)
    payload = {
        # "subject" — who the token is about. In this codebase the user id is the
        # email (UserRepository.create sets id=email). PyJWT 2.10+ requires this
        # claim to be a string, which it already is.
        "sub": user_id,
        # "issued at" — not required, but it makes a token's age readable.
        "iat": now,
        # "expires". PyJWT converts the datetime to the integer Unix timestamp the
        # spec calls for, and checks this claim automatically on the way back in.
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Verify a token and hand back the user id it was issued for.

    Raises InvalidToken for every way a token can fail to be trustworthy —
    expired, tampered with, malformed, missing a claim. One error code on
    purpose: which of those it was is not information an unauthenticated caller
    has any business learning.

    Translating PyJWT's exceptions here is what lets the auth guard call this
    without a try/except and without importing PyJWT at all. The library stays
    sealed inside this file.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            # HS256 is symmetric: the same secret signs and verifies.
            settings.JWT_SECRET_KEY,
            # An allow-list, and not optional. Left out, the decoder trusts the
            # `alg` field in the token's own header — which whoever sent the
            # token controls. Setting `alg: none` then makes an unsigned token
            # verify happily. The algorithm is our configuration's call.
            algorithms=[settings.JWT_ALGORITHM],
            # A token with no `exp` never expires. The verifier has to be the
            # strict side; trusting our own encoder to have set it is how a
            # forged claim-less token gets in.
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        # ExpiredSignatureError, InvalidSignatureError and MissingRequiredClaim
        # all subclass this one, so a single except covers expired, tampered,
        # malformed and incomplete alike.
        raise InvalidToken("invalid or expired token") from exc

    # Guaranteed present by the `require` option above.
    return payload["sub"]

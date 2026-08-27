from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings
from app.errors import InvalidToken

# Which table a token's subject lives in. User ids are emails, and the same
# address can be registered in both `users` and `admins`, so the subject alone
# does not say which one a token was issued for — this claim does.
ROLE_USER = "user"
ROLE_ADMIN = "admin"

# Helper for auth_service

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


# Access tokens

def create_access_token(
    user_id: str, role: str = ROLE_USER, expires_minutes: int | None = None
) -> str:
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token_claims(token: str) -> dict:
    """Return every verified claim, or raise InvalidToken."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            # Without an explicit allow-list the decoder trusts the token's own
            # `alg` header, so an unsigned `alg: none` token would verify.
            algorithms=[settings.JWT_ALGORITHM],
            # A token with no `exp` never expires. A token with no `role` does
            # not say what it is allowed to do, so it is not trusted with a
            # privilege level either.
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidToken("invalid or expired token") from exc

    return payload


def decode_access_token(token: str) -> str:
    """Return the user id from a valid token, or raise InvalidToken."""
    return decode_access_token_claims(token)["sub"]

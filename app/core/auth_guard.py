"""Who is making this request, and are they allowed to?

Three dependencies, narrowest first:

    get_current_user       a bank customer, and only a customer
    get_current_admin      an admin, and only an admin
    get_current_principal  either, with `role` saying which

`get_current_principal` is for routes both sides genuinely need — listing
accounts backs the customer's own overview page and the admin dashboard alike.
Reach for one of the other two everywhere else: a route that accepts anyone is
a decision worth making on purpose, not by default.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import ROLE_ADMIN, ROLE_USER, decode_access_token_claims
from app.errors import InvalidToken
from app.repositories.admin_repository import admin_repository
from app.repositories.user_repository import user_repository

# Read the Bearer token from the Authorization header. Not OAuth2PasswordBearer:
# that scheme has Swagger's Authorize dialog POST form-encoded `username`/
# `password` straight to `tokenUrl`, but `/auth/login` takes a JSON body keyed
# on `email` — the dialog's request would 422 every time. HTTPBearer instead
# gives Swagger a plain "paste your token" field; auto_error is off so a
# missing header falls through to `_unauthenticated()` below and stays a 401,
# not HTTPBearer's own 403.
bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT")

# Which repository owns each role's records. Admins and customers are separate
# tables on purpose, so a token minted for one can never resolve to the other.
_REPOSITORIES = {
    ROLE_USER: user_repository,
    ROLE_ADMIN: admin_repository,
}


def _unauthenticated() -> HTTPException:
    # One message for every way authentication can fail. Which way it was is not
    # information an unauthenticated caller has any business learning.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Return whoever the token is for — customer or admin — tagged with `role`."""
    if credentials is None:
        raise _unauthenticated()

    try:
        claims = decode_access_token_claims(credentials.credentials)
    except InvalidToken:
        raise _unauthenticated()

    repository = _REPOSITORIES.get(claims["role"])
    if repository is None:
        # A signed token carrying a role we do not issue. Nothing legitimate
        # mints one, so treat it as a forgery rather than guessing a default.
        raise _unauthenticated()

    record = repository.get_by_email(claims["sub"])
    if record is None:
        # Valid signature, but the account has been deleted since it was issued.
        raise _unauthenticated()

    return {**record, "role": claims["role"]}


def get_current_user(principal: dict = Depends(get_current_principal)) -> dict:
    """Return the authenticated customer. Admins are refused here."""
    if principal["role"] != ROLE_USER:
        # 401, not 403: to a customer-only route an admin is not a caller with
        # insufficient rights, it is the wrong kind of account entirely.
        raise _unauthenticated()
    return principal


def get_current_admin(principal: dict = Depends(get_current_principal)) -> dict:
    """Return the authenticated admin. Customers are refused here."""
    if principal["role"] != ROLE_ADMIN:
        # 403, not 401: the credentials are good, they just are not enough.
        # Answering 401 would invite the client to retry the same valid login.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return principal

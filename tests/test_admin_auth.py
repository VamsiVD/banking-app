"""Tests for the admin/customer boundary.

Two tables, two login routes, two kinds of token — and one thing that decides
which is which: the `role` claim. These cases are about the seam between them,
not about either side's own behaviour.

Why the claim exists rather than a table lookup: a user id *is* an email
(`UserRepository.create` sets `id=email`), so the same address can be registered
as both a customer and an admin. Without the claim, the two tokens are the same
token.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.core.security import ROLE_ADMIN, ROLE_USER, create_access_token

from conftest import DEFAULT_ADMIN_ID, DEFAULT_OWNER_ID


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# the token itself
# --------------------------------------------------------------------------


def test_admin_login_returns_a_token_not_a_profile(client, admin_headers):
    """The fixture only builds if /admin/login hands back an access_token."""
    assert admin_headers["Authorization"].startswith("Bearer ")


def test_an_admin_token_says_it_is_an_admin(client, admin_headers):
    token = admin_headers["Authorization"].removeprefix("Bearer ")

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["sub"] == DEFAULT_ADMIN_ID
    assert claims["role"] == ROLE_ADMIN


def test_a_customer_token_says_it_is_a_customer(client, auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")

    assert jwt.decode(token, options={"verify_signature": False})["role"] == ROLE_USER


def test_a_token_without_a_role_is_refused(client, make_account):
    """Fails if decode() loses "role" from its `require` list.

    Correctly signed and unexpired — the only thing wrong with it is that it
    does not say what it is allowed to do.
    """
    make_account("ACC-1")
    now = datetime.now(timezone.utc)
    roleless = jwt.encode(
        {"sub": DEFAULT_OWNER_ID, "iat": now, "exp": now + timedelta(minutes=30)},
        get_settings().JWT_SECRET_KEY,
        algorithm="HS256",
    )

    assert client.get("/accounts/", headers=_bearer(roleless)).status_code == 401


def test_a_token_with_an_unknown_role_is_refused(client, make_account):
    """A role we never issue resolves to no repository, so it authenticates nobody."""
    make_account("ACC-1")
    invented = create_access_token(DEFAULT_OWNER_ID, role="superuser")

    assert client.get("/accounts/", headers=_bearer(invented)).status_code == 401


# --------------------------------------------------------------------------
# what each token reaches
# --------------------------------------------------------------------------


def test_an_admin_may_read_accounts(client, admin_headers, make_account):
    """The dashboard's main read. Admins are not customers, so this needs saying."""
    make_account("ACC-1")

    r = client.get("/accounts/", headers=admin_headers)

    assert r.status_code == 200
    assert [a["account_number"] for a in r.json()] == ["ACC-1"]


def test_an_admin_may_freeze_an_account(client, admin_headers, make_account):
    make_account("ACC-1")

    r = client.patch("/accounts/ACC-1", json={"status": "frozen"}, headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["status"] == "frozen"


@pytest.mark.parametrize("status_value", ["frozen", "closed"])
def test_a_customer_may_not_change_an_account(client, auth_headers, make_account, status_value):
    """The gap this branch closes: any logged-in customer could freeze any account."""
    make_account("ACC-1")

    r = client.patch("/accounts/ACC-1", json={"status": status_value}, headers=auth_headers)

    assert r.status_code == 403
    assert client.get("/accounts/ACC-1", headers=auth_headers).json()["status"] == "active"


def test_a_customer_may_not_delete_an_account(client, auth_headers, make_account):
    make_account("ACC-1")

    assert client.delete("/accounts/ACC-1", headers=auth_headers).status_code == 403
    assert client.get("/accounts/ACC-1", headers=auth_headers).status_code == 200


def test_a_customer_token_does_not_reach_the_admin_routes(client, auth_headers, admin_headers):
    """403, not 401: the credentials are fine, they are just the wrong ones."""
    assert client.get("/admin/", headers=auth_headers).status_code == 403
    assert client.get("/admin/", headers=admin_headers).status_code == 200


def test_an_admin_may_read_transfer_history(client, admin_headers, make_account):
    """Also a dashboard read. Guarded by principal, not by customer."""
    make_account("ACC-1")

    r = client.get("/transfers?limit=10", headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["items"] == []


def test_an_admin_token_does_not_reach_the_customer_routes(client, admin_headers, make_account):
    """The other direction. An admin is not a bank customer and has no money to move.

    Reading the history is fine; being the source of a transfer is not.
    """
    make_account("ACC-1")
    make_account("ACC-2")

    r = client.post(
        "/transfers",
        json={
            "from_account_number": "ACC-1",
            "to_account_number": "ACC-2",
            "amount": "10.00",
        },
        headers=admin_headers,
    )

    assert r.status_code == 401


def test_the_admin_routes_still_refuse_an_anonymous_caller(client):
    assert client.get("/admin/").status_code == 401

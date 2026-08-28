"""Tests for the /accounts CRUD slice.

The important one is test_accounts_and_deposits_agree. Before this branch, this
router kept its own list of dicts: GET /accounts/1001 reported 1500.0 while a
deposit against the same account reported 1510.00, because they were two
different datasets pretending to be one.
"""

from decimal import Decimal

import pytest

from app import db
from app.core import store

from conftest import DEFAULT_OWNER_ID, ensure_owner


def err(response) -> str:
    return response.json()["error"]["code"]


def new_account(holder="New Holder", kind="checking",
                balance="250.00", status="active", owner_id=DEFAULT_OWNER_ID, **extra):
    """account_number is deliberately absent: the server assigns it now
    (store.get_next_account_number()), the client no longer supplies one.
    Pass account_number=... through **extra if a test needs to check that
    an explicit one is rejected.
    """
    return {
        "account_holder_name": holder,
        "account_type": kind,
        "status": status,
        "balance": balance,
        "currency": "USD",
        "owner_id": owner_id,
        **extra,
    }


# --------------------------------------------------------------------------
# the split-brain this branch closes
# --------------------------------------------------------------------------


def test_accounts_and_the_store_agree(client, auth_headers, make_account, db_session):
    """One dataset.

    This router used to keep its own list of dicts, so it reported 1500.0 while
    the store reported 1510.00 for the same account. A balance changed through
    the store is now visible here immediately.

    Goes through the store rather than POST /accounts/{n}/deposit because that
    endpoint is currently a stub — see the skips in test_transactions.py.
    """
    make_account("ACC-1", balance="100.00")

    with store.transaction():
        account = store.get("ACC-1")
        store.put(account.model_copy(update={"balance": Decimal("110.00")}))

    assert client.get("/accounts/ACC-1", headers=auth_headers).json()["balance"] == "110.00"


def test_an_account_created_through_the_api_is_visible_to_the_store(client, auth_headers, db_session):
    """Creating and then using an account used to be impossible across two stores."""
    ensure_owner()
    r = client.post("/accounts/", json=new_account(balance="0.00"), headers=auth_headers)
    assert r.status_code == 201
    account_number = r.json()["account_number"]

    with db.session_scope():
        assert store.get(account_number) is not None

    with store.transaction():
        account = store.get(account_number)
        store.put(account.model_copy(update={"balance": Decimal("75.00")}))
        store.record(account_number, "deposit", Decimal("75.00"), "USD", Decimal("75.00"))

    assert client.get(f"/accounts/{account_number}", headers=auth_headers).json()["balance"] == "75.00"


def test_balances_are_json_strings_not_floats(client, auth_headers, make_account):
    """The old list stored 1500.0. A JSON number is a float, and floats lose cents."""
    make_account("ACC-1", balance="1500.00")

    assert client.get("/accounts/ACC-1", headers=auth_headers).json()["balance"] == "1500.00"
    assert isinstance(client.get("/accounts/", headers=auth_headers).json()[0]["balance"], str)


# --------------------------------------------------------------------------
# read
# --------------------------------------------------------------------------


def test_list_is_empty_before_seeding(client, auth_headers):
    """No hardcoded accounts. An empty database lists nothing."""
    assert client.get("/accounts/", headers=auth_headers).json() == []


def test_list_returns_every_account_in_order(client, auth_headers, make_account):
    make_account("ACC-2")
    make_account("ACC-1")

    numbers = [a["account_number"] for a in client.get("/accounts/", headers=auth_headers).json()]

    assert numbers == ["ACC-1", "ACC-2"]


def test_fetching_an_unknown_account_is_404(client, auth_headers):
    r = client.get("/accounts/NOPE", headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "account_not_found"


# --------------------------------------------------------------------------
# create
# --------------------------------------------------------------------------


def test_create_persists_the_account(client, auth_headers, db_session):
    ensure_owner()
    r = client.post("/accounts/", json=new_account(balance="250.00"), headers=auth_headers)

    assert r.status_code == 201
    account_number = r.json()["account_number"]
    assert store.get(account_number).balance == Decimal("250.00")


def test_create_auto_generates_an_incrementing_account_number(client, auth_headers):
    """The server assigns account numbers now (store.get_next_account_number());
    the client no longer supplies one. Numbers increment across creates."""
    ensure_owner()
    first = client.post("/accounts/", json=new_account(), headers=auth_headers).json()
    second = client.post("/accounts/", json=new_account(), headers=auth_headers).json()

    assert int(second["account_number"]) == int(first["account_number"]) + 1


def test_creating_an_account_with_an_explicit_account_number_is_refused(client, auth_headers):
    """account_number is no longer a field on BankAccountCreate, so sending one
    trips extra="forbid" — the same 422 any other unknown field gets."""
    ensure_owner()
    r = client.post(
        "/accounts/", json=new_account(account_number="CUSTOM-42"), headers=auth_headers
    )

    assert r.status_code == 422


def test_a_float_balance_with_too_many_decimals_is_refused(client, auth_headers):
    r = client.post("/accounts/", json=new_account(balance="10.005"), headers=auth_headers)

    assert r.status_code == 422


def test_unknown_field_is_rejected(client, auth_headers):
    r = client.post("/accounts/", json=new_account(nickname="rainy day"), headers=auth_headers)

    assert r.status_code == 422


# --------------------------------------------------------------------------
# update
# --------------------------------------------------------------------------


def test_patch_changes_the_status(client, auth_headers, admin_headers, make_account):
    make_account("ACC-1")

    r = client.patch("/accounts/ACC-1", json={"status": "frozen"}, headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["status"] == "frozen"
    assert client.get("/accounts/ACC-1", headers=auth_headers).json()["status"] == "frozen"


def test_a_frozen_account_then_refuses_a_transfer(client, auth_headers, admin_headers, make_account):
    """The status change reaches the money endpoints, because there is one store."""
    make_account("ACC-1")
    make_account("ACC-2")
    client.patch("/accounts/ACC-1", json={"status": "frozen"}, headers=admin_headers)

    r = client.post(
        "/transfers",
        json={
            "from_account_number": "ACC-1",
            "to_account_number": "ACC-2",
            "amount": "10.00",
        }, headers=auth_headers,
    )

    assert r.status_code == 409
    assert err(r) == "account_not_active"


def test_patching_an_unknown_status_is_refused(client, admin_headers, make_account):
    make_account("ACC-1")

    assert client.patch("/accounts/ACC-1", json={"status": "sleepy"}, headers=admin_headers).status_code == 422


def test_patching_an_unknown_account_is_404(client, admin_headers):
    r = client.patch("/accounts/NOPE", json={"status": "frozen"}, headers=admin_headers)

    assert r.status_code == 404
    assert err(r) == "account_not_found"


# --------------------------------------------------------------------------
# delete
# --------------------------------------------------------------------------


def test_delete_removes_an_untouched_account(client, auth_headers, admin_headers, make_account):
    make_account("ACC-1")

    assert client.delete("/accounts/ACC-1", headers=admin_headers).status_code == 200
    assert client.get("/accounts/ACC-1", headers=auth_headers).status_code == 404


def test_deleting_an_unknown_account_is_404(client, admin_headers):
    r = client.delete("/accounts/NOPE", headers=admin_headers)

    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_an_account_with_history_cannot_be_deleted(client, auth_headers, admin_headers, make_account, db_session):
    """A ledger is only auditable if entries cannot be orphaned."""
    make_account("ACC-1")
    with store.transaction():
        store.record("ACC-1", "deposit", Decimal("10.00"), "USD", Decimal("110.00"))

    r = client.delete("/accounts/ACC-1", headers=admin_headers)

    assert r.status_code == 409
    assert err(r) == "account_has_history"
    assert client.get("/accounts/ACC-1", headers=auth_headers).status_code == 200

"""Tests for the /accounts CRUD slice.

The important one is test_accounts_and_deposits_agree. Before this branch, this
router kept its own list of dicts: GET /accounts/1001 reported 1500.0 while a
deposit against the same account reported 1510.00, because they were two
different datasets pretending to be one.
"""

from decimal import Decimal

import pytest

from app.core import store


def err(response) -> str:
    return response.json()["error"]["code"]


def new_account(number="ACC-9", holder="New Holder", kind="checking",
                balance="250.00", status="active", **extra):
    return {
        "account_number": number,
        "account_holder_name": holder,
        "account_type": kind,
        "status": status,
        "balance": balance,
        "currency": "USD",
        **extra,
    }


# --------------------------------------------------------------------------
# the split-brain this branch closes
# --------------------------------------------------------------------------


def test_accounts_and_deposits_agree(client, make_account):
    """One dataset. The router and the money endpoints see the same balance."""
    make_account("ACC-1", balance="100.00")

    client.post("/accounts/ACC-1/deposit", json={"amount": "10.00"})

    assert client.get("/accounts/ACC-1").json()["balance"] == "110.00"


def test_an_account_created_through_the_api_can_receive_money(client):
    """Creating and then using an account used to be impossible across the two stores."""
    assert client.post("/accounts/", json=new_account("ACC-9", balance="0.00")).status_code == 201

    r = client.post("/accounts/ACC-9/deposit", json={"amount": "75.00"})

    assert r.status_code == 200
    assert client.get("/accounts/ACC-9").json()["balance"] == "75.00"


def test_balances_are_json_strings_not_floats(client, make_account):
    """The old list stored 1500.0. A JSON number is a float, and floats lose cents."""
    make_account("ACC-1", balance="1500.00")

    assert client.get("/accounts/ACC-1").json()["balance"] == "1500.00"
    assert isinstance(client.get("/accounts/").json()[0]["balance"], str)


# --------------------------------------------------------------------------
# read
# --------------------------------------------------------------------------


def test_list_is_empty_before_seeding(client):
    """No hardcoded accounts. An empty database lists nothing."""
    assert client.get("/accounts/").json() == []


def test_list_returns_every_account_in_order(client, make_account):
    make_account("ACC-2")
    make_account("ACC-1")

    numbers = [a["account_number"] for a in client.get("/accounts/").json()]

    assert numbers == ["ACC-1", "ACC-2"]


def test_fetching_an_unknown_account_is_404(client):
    r = client.get("/accounts/NOPE")

    assert r.status_code == 404
    assert err(r) == "account_not_found"


# --------------------------------------------------------------------------
# create
# --------------------------------------------------------------------------


def test_create_persists_the_account(client, db_session):
    r = client.post("/accounts/", json=new_account("ACC-9", balance="250.00"))

    assert r.status_code == 201
    assert store.get("ACC-9").balance == Decimal("250.00")


def test_create_honours_the_account_number_from_the_body(client):
    """It used to invent str(1000 + len(accounts) + 1), which reuses a number
    as soon as anything is deleted."""
    client.post("/accounts/", json=new_account("CUSTOM-42"))

    assert client.get("/accounts/CUSTOM-42").status_code == 200


def test_creating_a_duplicate_number_is_refused(client, make_account):
    make_account("ACC-1")

    r = client.post("/accounts/", json=new_account("ACC-1"))

    assert r.status_code == 409
    assert err(r) == "duplicate_account"


def test_a_float_balance_with_too_many_decimals_is_refused(client):
    r = client.post("/accounts/", json=new_account(balance="10.005"))

    assert r.status_code == 422


def test_unknown_field_is_rejected(client):
    r = client.post("/accounts/", json=new_account(nickname="rainy day"))

    assert r.status_code == 422


# --------------------------------------------------------------------------
# update
# --------------------------------------------------------------------------


def test_patch_changes_the_status(client, make_account):
    make_account("ACC-1")

    r = client.patch("/accounts/ACC-1", json={"status": "frozen"})

    assert r.status_code == 200
    assert r.json()["status"] == "frozen"
    assert client.get("/accounts/ACC-1").json()["status"] == "frozen"


def test_a_frozen_account_then_refuses_money(client, make_account):
    """The status change reaches the money endpoints, because there is one store."""
    make_account("ACC-1")
    client.patch("/accounts/ACC-1", json={"status": "frozen"})

    assert client.post("/accounts/ACC-1/deposit", json={"amount": "10.00"}).status_code == 409


def test_patching_an_unknown_status_is_refused(client, make_account):
    make_account("ACC-1")

    assert client.patch("/accounts/ACC-1", json={"status": "sleepy"}).status_code == 422


def test_patching_an_unknown_account_is_404(client):
    r = client.patch("/accounts/NOPE", json={"status": "frozen"})

    assert r.status_code == 404
    assert err(r) == "account_not_found"


# --------------------------------------------------------------------------
# delete
# --------------------------------------------------------------------------


def test_delete_removes_an_untouched_account(client, make_account):
    make_account("ACC-1")

    assert client.delete("/accounts/ACC-1").status_code == 200
    assert client.get("/accounts/ACC-1").status_code == 404


def test_deleting_an_unknown_account_is_404(client):
    r = client.delete("/accounts/NOPE")

    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_an_account_with_history_cannot_be_deleted(client, make_account):
    """A ledger is only auditable if entries cannot be orphaned."""
    make_account("ACC-1")
    client.post("/accounts/ACC-1/deposit", json={"amount": "10.00"})

    r = client.delete("/accounts/ACC-1")

    assert r.status_code == 409
    assert err(r) == "account_has_history"
    assert client.get("/accounts/ACC-1").status_code == 200

"""Tests for the transfers slice: POST /transfers.

Reconstructed from the endpoint's behaviour — the original file was lost before it
was ever committed, and survived only as a .pyc in tests/__pycache__. The test
names come from that bytecode, so the coverage matches what was there.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from app.core import store


def err(response) -> str:
    """The error code out of the shared envelope."""
    return response.json()["error"]["code"]


def transfer(client, source="ACC-1", target="ACC-2", amount="25.00", **extra):
    body = {
        "from_account_number": source,
        "to_account_number": target,
        "amount": amount,
        **extra,
    }
    return client.post("/transfers", json=body)


# --------------------------------------------------------------------------
# the happy path
# --------------------------------------------------------------------------


def test_transfer_moves_money_between_accounts(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="10.00")

    r = transfer(client, amount="40.00")

    assert r.status_code == 201
    assert store.get("ACC-1").balance == Decimal("60.00")
    assert store.get("ACC-2").balance == Decimal("50.00")


def test_transfer_writes_both_sides_with_counterparties(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, amount="30.00", description="rent")
    body = r.json()

    assert body["debit"]["type"] == "transfer_out"
    assert body["debit"]["counterparty"] == "ACC-2"
    assert body["credit"]["type"] == "transfer_in"
    assert body["credit"]["counterparty"] == "ACC-1"

    # One entry each side, both carrying the description.
    assert [e.description for e in store.for_account("ACC-1")] == ["rent"]
    assert [e.description for e in store.for_account("ACC-2")] == ["rent"]


def test_transfer_conserves_the_total(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="55.00")
    before = Decimal("155.00")

    transfer(client, amount="72.50")

    after = store.get("ACC-1").balance + store.get("ACC-2").balance
    assert after == before


def test_transfer_may_empty_the_source_exactly(client, make_account):
    make_account("ACC-1", balance="40.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, amount="40.00")

    assert r.status_code == 201
    assert store.get("ACC-1").balance == Decimal("0.00")


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


def test_overdraft_is_refused_and_changes_nothing(client, make_account):
    make_account("ACC-1", balance="30.00")
    make_account("ACC-2", balance="10.00")

    r = transfer(client, amount="30.01")

    assert r.status_code == 409
    assert err(r) == "insufficient_funds"
    assert store.get("ACC-1").balance == Decimal("30.00")
    assert store.get("ACC-2").balance == Decimal("10.00")
    assert store.list_transactions() == []


def test_transfer_across_currencies_is_refused(client, make_account):
    make_account("ACC-1", balance="100.00", currency="USD")
    make_account("ACC-2", balance="0.00", currency="EUR")

    r = transfer(client)

    assert r.status_code == 409
    assert err(r) == "currency_mismatch"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_from_unknown_account_is_404(client, make_account):
    make_account("ACC-2", balance="10.00")

    r = transfer(client, source="NOPE", target="ACC-2")

    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_transfer_to_unknown_account_is_404(client, make_account):
    make_account("ACC-1", balance="100.00")

    r = transfer(client, source="ACC-1", target="NOPE")

    assert r.status_code == 404
    assert err(r) == "account_not_found"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_from_a_frozen_account_is_refused(client, make_account):
    make_account("ACC-1", balance="100.00", status="frozen")
    make_account("ACC-2", balance="0.00")

    r = transfer(client)

    assert r.status_code == 409
    assert err(r) == "account_not_active"


def test_transfer_into_a_closed_account_is_refused(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00", status="closed")

    r = transfer(client)

    assert r.status_code == 409
    assert err(r) == "account_not_active"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_to_self_is_refused(client, make_account):
    make_account("ACC-1", balance="100.00")

    r = transfer(client, source="ACC-1", target="ACC-1")

    # Knowable from the body alone, so it is a validation error, not a domain one.
    assert r.status_code == 422
    assert err(r) == "validation_error"


def test_non_positive_amounts_are_rejected(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    for amount in ("0.00", "-5.00"):
        r = transfer(client, amount=amount)
        assert r.status_code == 422, amount

    assert store.get("ACC-1").balance == Decimal("100.00")


def test_unknown_field_is_rejected(client, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    # extra="forbid": an unexpected key is a client bug, and dropping it hides it.
    r = transfer(client, fee="1.00")

    assert r.status_code == 422


# --------------------------------------------------------------------------
# money is Decimal
# --------------------------------------------------------------------------


def test_amounts_are_json_strings_not_floats(client, make_account):
    """Money crosses the wire as a string; a JSON number would be a float."""
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    body = transfer(client, amount="40.00").json()

    assert body["debit"]["amount"] == "40.00"
    assert body["debit"]["balance_after"] == "60.00"
    assert isinstance(body["credit"]["amount"], str)


def test_repeated_small_transfers_do_not_drift(client, make_account):
    """The reason money is Decimal: 0.1 + 0.2 != 0.3 in float."""
    make_account("ACC-1", balance="10.00")
    make_account("ACC-2", balance="0.00")

    for _ in range(100):
        assert transfer(client, amount="0.10").status_code == 201

    assert store.get("ACC-1").balance == Decimal("0.00")
    assert store.get("ACC-2").balance == Decimal("10.00")


def test_concurrent_transfers_cannot_overdraw(client, make_account):
    """The row lock's reason for existing.

    150 threads race to move 1.00 out of a balance of 100.00. Whatever order they
    interleave in, exactly 100 may succeed. Without SELECT ... FOR UPDATE around
    read-check-write, two of them read the same balance, both pass the check, and
    the account goes negative.
    """
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    with ThreadPoolExecutor(max_workers=32) as pool:
        responses = list(
            pool.map(lambda _: transfer(client, amount="1.00"), range(150))
        )

    assert sum(r.status_code == 201 for r in responses) == 100
    assert store.get("ACC-1").balance == Decimal("0.00")
    assert store.get("ACC-2").balance == Decimal("100.00")

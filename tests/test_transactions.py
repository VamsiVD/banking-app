"""Tests for the transactions slice: deposit, withdraw, transfer.

Deposit and withdraw answer 200 with the ledger entry itself — the `Transaction`,
not a wrapper — because `routers/transactions.py` declares
`response_model=Transaction` and delegates to `services/transaction_service.py`.
Refusals come back in the shared `{"error": {"code", "message"}}` envelope like
everything else, since that service raises the `app/errors.py` classes.
"""

from decimal import Decimal

from app.core import store


def err(response) -> str:
    """The error code out of the shared envelope."""
    return response.json()["error"]["code"]


# --------------------------------------------------------------------------
# deposit
# --------------------------------------------------------------------------


def test_deposit_credits_the_account(client, auth_headers, make_account):
    make_account(balance="100.00")
    r = client.post("/accounts/ACC-1/deposit", json={"amount": "40.50"}, headers=auth_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "deposit"
    assert body["balance_after"] == "140.50"
    assert store.get("ACC-1").balance == Decimal("140.50")


def test_deposit_writes_one_ledger_entry(client, auth_headers, make_account):
    make_account()
    client.post("/accounts/ACC-1/deposit", json={"amount": "10.00", "description": "payday"}, headers=auth_headers)

    entries = store.for_account("ACC-1")
    assert len(entries) == 1
    assert entries[0].description == "payday"
    assert entries[0].counterparty is None


def test_deposit_to_unknown_account_is_404(client, auth_headers):
    r = client.post("/accounts/NOPE/deposit", json={"amount": "10.00"}, headers=auth_headers)
    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_deposit_to_frozen_account_is_rejected(client, auth_headers, make_account):
    make_account(status="frozen")
    r = client.post("/accounts/ACC-1/deposit", json={"amount": "10.00"}, headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "account_not_active"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_non_positive_amounts_are_rejected(client, auth_headers, make_account):
    make_account()
    for amount in ("0", "-5.00"):
        r = client.post("/accounts/ACC-1/deposit", json={"amount": amount}, headers=auth_headers)
        assert r.status_code == 422, amount
        assert err(r) == "validation_error"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_unknown_field_is_rejected(client, auth_headers, make_account):
    make_account()
    r = client.post("/accounts/ACC-1/deposit", json={"amount": "10.00", "currency": "EUR"}, headers=auth_headers)
    assert r.status_code == 422
    assert err(r) == "validation_error"


# --------------------------------------------------------------------------
# withdraw
# --------------------------------------------------------------------------


def test_withdraw_debits_the_account(client, auth_headers, make_account):
    make_account(balance="100.00")
    r = client.post("/accounts/ACC-1/withdraw", json={"amount": "30.00"}, headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["type"] == "withdrawal"
    assert store.get("ACC-1").balance == Decimal("70.00")


def test_withdraw_may_empty_the_account_exactly(client, auth_headers, make_account):
    make_account(balance="100.00")
    r = client.post("/accounts/ACC-1/withdraw", json={"amount": "100.00"}, headers=auth_headers)

    assert r.status_code == 200
    assert store.get("ACC-1").balance == Decimal("0.00")


def test_overdraft_is_refused_and_changes_nothing(client, auth_headers, make_account):
    make_account(balance="50.00")
    r = client.post("/accounts/ACC-1/withdraw", json={"amount": "50.01"}, headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "insufficient_funds"
    assert store.get("ACC-1").balance == Decimal("50.00")
    assert store.for_account("ACC-1") == []


# --------------------------------------------------------------------------
# transfer
# --------------------------------------------------------------------------


def test_transfer_moves_money_between_accounts(client, auth_headers, make_account):
    make_account("AAA", balance="100.00")
    make_account("BBB", balance="0.00")

    r = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "40.00"}, headers=auth_headers,
    )

    assert r.status_code == 201
    assert store.get("AAA").balance == Decimal("60.00")
    assert store.get("BBB").balance == Decimal("40.00")


def test_transfer_writes_both_sides_with_counterparties(client, auth_headers, make_account):
    make_account("AAA", balance="100.00")
    make_account("BBB", balance="0.00")

    body = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "40.00"}, headers=auth_headers,
    ).json()

    assert body["debit"]["type"] == "transfer_out"
    assert body["debit"]["counterparty"] == "BBB"
    assert body["credit"]["type"] == "transfer_in"
    assert body["credit"]["counterparty"] == "AAA"
    assert len(store.list_transactions()) == 2


def test_transfer_conserves_the_total(client, auth_headers, make_account):
    make_account("AAA", balance="100.00")
    make_account("BBB", balance="25.00")

    client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "33.33"}, headers=auth_headers,
    )

    total = sum(a.balance for a in store.list_all())
    assert total == Decimal("125.00")


def test_transfer_across_currencies_is_refused(client, auth_headers, make_account):
    make_account("AAA", balance="100.00", currency="USD")
    make_account("BBB", balance="0.00", currency="EUR")

    r = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "10.00"}, headers=auth_headers,
    )

    assert r.status_code == 409
    assert err(r) == "currency_mismatch"
    assert store.get("AAA").balance == Decimal("100.00")


def test_failed_transfer_leaves_both_sides_untouched(client, auth_headers, make_account):
    make_account("AAA", balance="10.00")
    make_account("BBB", balance="5.00")

    r = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "999.00"}, headers=auth_headers,
    )

    assert r.status_code == 409
    assert err(r) == "insufficient_funds"
    assert store.get("AAA").balance == Decimal("10.00")
    assert store.get("BBB").balance == Decimal("5.00")
    assert store.list_transactions() == []


def test_transfer_to_self_is_refused(client, auth_headers, make_account):
    make_account("AAA", balance="100.00")
    r = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "AAA", "amount": "10.00"}, headers=auth_headers,
    )

    assert r.status_code == 422
    assert store.get("AAA").balance == Decimal("100.00")


def test_transfer_from_unknown_account_is_404(client, auth_headers, make_account):
    make_account("BBB")
    r = client.post(
        "/transfers",
        json={"from_account_number": "NOPE", "to_account_number": "BBB", "amount": "10.00"}, headers=auth_headers,
    )
    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_transfer_into_a_closed_account_is_refused(client, auth_headers, make_account):
    make_account("AAA", balance="100.00")
    make_account("BBB", balance="0.00", status="closed")

    r = client.post(
        "/transfers",
        json={"from_account_number": "AAA", "to_account_number": "BBB", "amount": "10.00"}, headers=auth_headers,
    )

    assert r.status_code == 409
    assert err(r) == "account_not_active"
    assert store.get("AAA").balance == Decimal("100.00")


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------


def test_amounts_are_json_strings_not_floats(client, auth_headers, make_account):
    """Money crosses the wire as a string; a JSON number would be a float."""
    make_account(balance="100.00")
    body = client.post("/accounts/ACC-1/deposit", json={"amount": "0.10"}, headers=auth_headers).json()

    assert body["amount"] == "0.10"
    assert isinstance(body["balance_after"], str)


def test_repeated_small_deposits_do_not_drift(client, auth_headers, make_account):
    """The reason money is Decimal: 0.1 + 0.2 != 0.3 in float."""
    make_account(balance="0.00")
    for _ in range(10):
        client.post("/accounts/ACC-1/deposit", json={"amount": "0.10"}, headers=auth_headers)

    assert store.get("ACC-1").balance == Decimal("1.00")


def test_concurrent_withdrawals_cannot_overdraw(client, auth_headers, make_account):
    """The row lock's reason for existing.

    150 threads race to withdraw 1.00 from a balance of 100.00. Whatever order
    they interleave in, exactly 100 may succeed. Without SELECT ... FOR UPDATE
    around read-check-write, two threads read the same balance, both pass the
    check, and the account goes negative.
    """
    from concurrent.futures import ThreadPoolExecutor

    make_account(balance="100.00")

    with ThreadPoolExecutor(max_workers=32) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/accounts/ACC-1/withdraw", json={"amount": "1.00"}, headers=auth_headers),
                range(150),
            )
        )

    succeeded = sum(r.status_code == 200 for r in responses)
    assert succeeded == 100
    assert sum(r.status_code == 409 for r in responses) == 50
    assert store.get("ACC-1").balance == Decimal("0.00")
    # One ledger entry per success, never one per attempt.
    assert len(store.list_transactions()) == succeeded

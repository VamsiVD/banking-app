"""Tests for the transfers slice: POST /transfers, GET /transfers.

The write cases were reconstructed from the endpoint's behaviour — the original
file was lost before it was ever committed and survived only as a .pyc in
tests/__pycache__ — so their names match what was there.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from app.core import store


def err(response) -> str:
    """The error code out of the shared envelope."""
    return response.json()["error"]["code"]


def transfer(client, source="ACC-1", target="ACC-2", amount="25.00", *, auth_headers, **extra):
    body = {
        "from_account_number": source,
        "to_account_number": target,
        "amount": amount,
        **extra,
    }
    return client.post("/transfers", json=body, headers=auth_headers)


# --------------------------------------------------------------------------
# the happy path
# --------------------------------------------------------------------------


def test_transfer_moves_money_between_accounts(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="10.00")

    r = transfer(client, amount="40.00", auth_headers=auth_headers)

    assert r.status_code == 201
    assert store.get("ACC-1").balance == Decimal("60.00")
    assert store.get("ACC-2").balance == Decimal("50.00")


def test_transfer_writes_both_sides_with_counterparties(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, amount="30.00", description="rent", auth_headers=auth_headers)
    body = r.json()

    assert body["debit"]["type"] == "transfer_out"
    assert body["debit"]["counterparty"] == "ACC-2"
    assert body["credit"]["type"] == "transfer_in"
    assert body["credit"]["counterparty"] == "ACC-1"

    # One entry each side, both carrying the description.
    assert [e.description for e in store.for_account("ACC-1")] == ["rent"]
    assert [e.description for e in store.for_account("ACC-2")] == ["rent"]


def test_transfer_conserves_the_total(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="55.00")
    before = Decimal("155.00")

    transfer(client, amount="72.50", auth_headers=auth_headers)

    after = store.get("ACC-1").balance + store.get("ACC-2").balance
    assert after == before


def test_transfer_may_empty_the_source_exactly(client, auth_headers, make_account):
    make_account("ACC-1", balance="40.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, amount="40.00", auth_headers=auth_headers)

    assert r.status_code == 201
    assert store.get("ACC-1").balance == Decimal("0.00")


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


def test_overdraft_is_refused_and_changes_nothing(client, auth_headers, make_account):
    make_account("ACC-1", balance="30.00")
    make_account("ACC-2", balance="10.00")

    r = transfer(client, amount="30.01", auth_headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "insufficient_funds"
    assert store.get("ACC-1").balance == Decimal("30.00")
    assert store.get("ACC-2").balance == Decimal("10.00")
    assert store.list_transactions() == []


def test_transfer_across_currencies_is_refused(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00", currency="USD")
    make_account("ACC-2", balance="0.00", currency="EUR")

    r = transfer(client, auth_headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "currency_mismatch"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_from_unknown_account_is_404(client, auth_headers, make_account):
    make_account("ACC-2", balance="10.00")

    r = transfer(client, source="NOPE", target="ACC-2", auth_headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "account_not_found"


def test_transfer_to_unknown_account_is_404(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")

    r = transfer(client, source="ACC-1", target="NOPE", auth_headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "account_not_found"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_from_a_frozen_account_is_refused(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00", status="frozen")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, auth_headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "account_not_active"


def test_transfer_into_a_closed_account_is_refused(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00", status="closed")

    r = transfer(client, auth_headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "account_not_active"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_transfer_to_self_is_refused(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")

    r = transfer(client, source="ACC-1", target="ACC-1", auth_headers=auth_headers)

    # Knowable from the body alone, so it is a validation error, not a domain one.
    assert r.status_code == 422
    assert err(r) == "validation_error"


def test_non_positive_amounts_are_rejected(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    for amount in ("0.00", "-5.00"):
        r = transfer(client, amount=amount, auth_headers=auth_headers)
        assert r.status_code == 422, amount

    assert store.get("ACC-1").balance == Decimal("100.00")


def test_unknown_field_is_rejected(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    # extra="forbid": an unexpected key is a client bug, and dropping it hides it.
    r = transfer(client, fee="1.00", auth_headers=auth_headers)

    assert r.status_code == 422


# --------------------------------------------------------------------------
# money is Decimal
# --------------------------------------------------------------------------


def test_amounts_are_json_strings_not_floats(client, auth_headers, make_account):
    """Money crosses the wire as a string; a JSON number would be a float."""
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    body = transfer(client, amount="40.00", auth_headers=auth_headers).json()

    assert body["debit"]["amount"] == "40.00"
    assert body["debit"]["balance_after"] == "60.00"
    assert isinstance(body["credit"]["amount"], str)


def test_repeated_small_transfers_do_not_drift(client, auth_headers, make_account):
    """The reason money is Decimal: 0.1 + 0.2 != 0.3 in float."""
    make_account("ACC-1", balance="10.00")
    make_account("ACC-2", balance="0.00")

    for _ in range(100):
        assert transfer(client, amount="0.10", auth_headers=auth_headers).status_code == 201

    assert store.get("ACC-1").balance == Decimal("0.00")
    assert store.get("ACC-2").balance == Decimal("10.00")


def test_concurrent_transfers_cannot_overdraw(client, auth_headers, make_account):
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
            pool.map(lambda _: transfer(client, amount="1.00", auth_headers=auth_headers), range(150))
        )

    assert sum(r.status_code == 201 for r in responses) == 100
    assert store.get("ACC-1").balance == Decimal("0.00")
    assert store.get("ACC-2").balance == Decimal("100.00")


# --------------------------------------------------------------------------
# refusals the write path did not cover
# --------------------------------------------------------------------------


def test_transfer_from_an_inactive_account_is_refused(client, auth_headers, make_account):
    """`inactive` is a fourth status, not a synonym for frozen or closed."""
    make_account("ACC-1", balance="100.00", status="inactive")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, auth_headers=auth_headers)

    assert r.status_code == 409
    assert err(r) == "account_not_active"
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_an_amount_with_too_many_decimals_is_refused(client, auth_headers, make_account):
    """NUMERIC(18,2) cannot hold a third decimal, so neither can the request.

    Rejected at the edge rather than silently rounded: a bank that quietly turns
    10.005 into 10.01 has invented a cent.
    """
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, amount="10.005", auth_headers=auth_headers)

    assert r.status_code == 422
    assert store.get("ACC-1").balance == Decimal("100.00")


def test_an_over_long_description_is_refused(client, auth_headers, make_account):
    """The column is VARCHAR(200); the schema stops it before the database has to."""
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")

    r = transfer(client, description="x" * 201, auth_headers=auth_headers)

    assert r.status_code == 422
    assert store.list_transactions() == []


# --------------------------------------------------------------------------
# reading transfers back
# --------------------------------------------------------------------------


def make_transfers(client, make_account, *, auth_headers):
    """Three transfers between three accounts, oldest first: one, two, three.

    ACC-2 both sends and receives, which is what makes the account filter
    meaningful.
    """
    make_account("ACC-1", balance="500.00")
    make_account("ACC-2", balance="500.00")
    make_account("ACC-3", balance="500.00")

    transfer(client, "ACC-1", "ACC-2", "10.00", description="one", auth_headers=auth_headers)
    transfer(client, "ACC-2", "ACC-3", "20.00", description="two", auth_headers=auth_headers)
    transfer(client, "ACC-1", "ACC-3", "30.00", description="three", auth_headers=auth_headers)


def test_no_transfers_yet_is_an_empty_page_not_a_404(client, auth_headers):
    """"Nothing has happened" and "that does not exist" are different facts."""
    body = client.get("/transfers", headers=auth_headers).json()

    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_a_transfer_can_be_read_back(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")
    transfer(client, amount="40.00", description="rent", auth_headers=auth_headers)

    item = client.get("/transfers", headers=auth_headers).json()["items"][0]

    assert item["from_account_number"] == "ACC-1"
    assert item["to_account_number"] == "ACC-2"
    assert item["amount"] == "40.00"
    assert item["currency"] == "USD"
    assert item["description"] == "rent"


def test_transfers_come_back_newest_first(client, auth_headers, make_account):
    make_transfers(client, make_account, auth_headers=auth_headers)

    order = [i["description"] for i in client.get("/transfers", headers=auth_headers).json()["items"]]

    assert order == ["three", "two", "one"]


def test_only_transfers_are_listed(client, auth_headers, make_account):
    """A deposit moves money too, but it is not a transfer."""
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")
    client.post("/accounts/ACC-1/deposit", json={"amount": "5.00"}, headers=auth_headers)
    transfer(client, amount="10.00", auth_headers=auth_headers)

    body = client.get("/transfers", headers=auth_headers).json()

    assert body["total"] == 1
    assert body["items"][0]["amount"] == "10.00"


def test_filtering_by_account_matches_both_sides(client, auth_headers, make_account):
    """A transfer is as much yours when you received it as when you sent it."""
    make_transfers(client, make_account, auth_headers=auth_headers)

    got = [i["description"] for i in
           client.get("/transfers", params={"account_number": "ACC-2"}, headers=auth_headers).json()["items"]]

    # "two" ACC-2 sent, "one" it received. "three" never touched it.
    assert got == ["two", "one"]


def test_filtering_by_an_account_with_no_transfers_is_empty(client, auth_headers, make_account):
    make_transfers(client, make_account, auth_headers=auth_headers)

    body = client.get("/transfers", params={"account_number": "NOBODY"}, headers=auth_headers).json()

    assert body["items"] == []
    assert body["total"] == 0


def test_total_counts_every_match_not_just_the_page(client, auth_headers, make_account):
    """The reason for the envelope: 2 of 3 has to be distinguishable from 2 of 2."""
    make_transfers(client, make_account, auth_headers=auth_headers)

    body = client.get("/transfers", params={"limit": 2}, headers=auth_headers).json()

    assert len(body["items"]) == 2
    assert body["total"] == 3


def test_offset_walks_through_the_pages(client, auth_headers, make_account):
    make_transfers(client, make_account, auth_headers=auth_headers)

    first = client.get("/transfers", params={"limit": 2, "offset": 0}, headers=auth_headers).json()
    second = client.get("/transfers", params={"limit": 2, "offset": 2}, headers=auth_headers).json()

    assert [i["description"] for i in first["items"]] == ["three", "two"]
    assert [i["description"] for i in second["items"]] == ["one"]
    assert second["total"] == 3


def test_limit_is_capped(client, auth_headers, make_account):
    """Without a ceiling, ?limit=1000000 is a way to make the server do work."""
    make_transfers(client, make_account, auth_headers=auth_headers)

    r = client.get("/transfers", params={"limit": 10_000}, headers=auth_headers)

    assert r.status_code == 422


def test_one_transfer_by_id(client, auth_headers, make_account):
    make_account("ACC-1", balance="100.00")
    make_account("ACC-2", balance="0.00")
    transfer(client, amount="40.00", description="rent", auth_headers=auth_headers)
    listed = client.get("/transfers", headers=auth_headers).json()["items"][0]

    r = client.get(f"/transfers/{listed['id']}", headers=auth_headers)

    assert r.status_code == 200
    assert r.json() == listed


def test_an_unknown_transfer_id_is_404(client, auth_headers):
    r = client.get("/transfers/nosuchid", headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "transfer_not_found"


def test_a_deposits_id_is_not_a_transfer(client, auth_headers, make_account):
    """Both live in the same table; only one of them is a transfer."""
    make_account("ACC-1", balance="100.00")
    deposit_id = client.post(
        "/accounts/ACC-1/deposit", json={"amount": "5.00"}
    , headers=auth_headers).json()["id"]

    r = client.get(f"/transfers/{deposit_id}", headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "transfer_not_found"

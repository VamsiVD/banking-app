"""Tests for the database foundation itself.

The other two files test banking rules and would pass against a dict. These test
the things that are only true because there is a real database underneath:
persistence, rollback, and constraints the application cannot talk its way past.

If you are adding a table, this is the file that tells you whether the plumbing
still holds.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import db
from app.core import store
from app.errors import DuplicateAccount
from app.api_schemas.account_schema import BankAccount

from conftest import DEFAULT_OWNER_ID, ensure_owner


def an_account(number="ACC-1", balance="100.00", status="active", currency="USD",
               owner_id=DEFAULT_OWNER_ID):
    ensure_owner(owner_id)
    return BankAccount(
        account_number=number,
        account_holder_name="Test Holder",
        account_type="checking",
        status=status,
        balance=Decimal(balance),
        currency=currency,
        date_opened=date.today(),
        owner_id=owner_id,
    )


# --------------------------------------------------------------------------
# it is actually persistent
# --------------------------------------------------------------------------


def test_data_survives_into_a_fresh_session(db_session):
    """The point of the whole exercise: state outlives the thing that wrote it.

    A new session is a new connection with an empty identity map — the closest
    thing a test can get to restarting the server.
    """
    store.add(an_account("ACC-1", balance="250.00"))

    with db.session_scope():
        assert store.get("ACC-1").balance == Decimal("250.00")


def test_money_round_trips_as_decimal_not_float(db_session):
    """NUMERIC(18,2) in, Decimal out. A float column would lose this."""
    store.add(an_account("ACC-1", balance="12345678901234.56"))

    with db.session_scope():
        balance = store.get("ACC-1").balance

    assert isinstance(balance, Decimal)
    assert balance == Decimal("12345678901234.56")


# --------------------------------------------------------------------------
# transaction() is a rollback now, not just a lock
# --------------------------------------------------------------------------


def test_transaction_rolls_back_everything_on_an_error(db_session):
    """The upgrade over the mutex the store used to hold.

    A mutex prevents interleaving but cannot undo. If a transfer failed halfway
    through, the money had already moved. Now the whole block reverts.
    """
    store.add(an_account("ACC-1", balance="100.00"))
    store.add(an_account("ACC-2", balance="0.00"))

    with pytest.raises(RuntimeError):
        with store.transaction():
            store.put(store.get("ACC-1").model_copy(update={"balance": Decimal("0")}))
            store.put(store.get("ACC-2").model_copy(update={"balance": Decimal("100")}))
            store.record(
                "ACC-1", "transfer_out", Decimal("100"), "USD", Decimal("0")
            )
            raise RuntimeError("something went wrong after the money moved")

    with db.session_scope():
        assert store.get("ACC-1").balance == Decimal("100.00")
        assert store.get("ACC-2").balance == Decimal("0.00")
        assert store.list_transactions() == []


def test_nested_transactions_commit_once_at_the_outermost_block(db_session):
    """store.record() opens a transaction inside the one transfers.py holds.

    The inner block must join the outer one rather than committing early — a
    ledger entry that commits before the balance it describes is exactly the
    disagreement the ledger exists to prevent.
    """
    store.add(an_account("ACC-1", balance="100.00"))

    with pytest.raises(RuntimeError):
        with store.transaction():
            store.put(store.get("ACC-1").model_copy(update={"balance": Decimal("150")}))
            # Opens and closes its own store.transaction() internally.
            store.record("ACC-1", "deposit", Decimal("50"), "USD", Decimal("150"))
            raise RuntimeError("fail after the inner block finished")

    with db.session_scope():
        assert store.get("ACC-1").balance == Decimal("100.00")
        assert store.list_transactions() == []


# --------------------------------------------------------------------------
# the database enforces the rules too
# --------------------------------------------------------------------------


def test_database_refuses_a_negative_balance(db_session):
    """The CHECK holds even against a stray UPDATE from a psql prompt."""
    store.add(an_account("ACC-1", balance="100.00"))

    with pytest.raises(IntegrityError):
        with store.transaction():
            db_session.execute(
                text("UPDATE accounts SET balance = -1 WHERE account_number = 'ACC-1'")
            )


def test_database_refuses_an_unknown_account_type(db_session):
    ensure_owner()
    with pytest.raises(IntegrityError):
        with store.transaction():
            db_session.execute(
                text(
                    "INSERT INTO accounts (account_number, account_holder_name, "
                    "account_type, status, balance, currency, date_opened, owner_id) "
                    "VALUES ('X', 'N', 'savngs', 'active', 0, 'USD', CURRENT_DATE, :owner)"
                ),
                {"owner": DEFAULT_OWNER_ID},
            )


def test_database_refuses_a_lowercase_currency(db_session):
    ensure_owner()
    with pytest.raises(IntegrityError):
        with store.transaction():
            db_session.execute(
                text(
                    "INSERT INTO accounts (account_number, account_holder_name, "
                    "account_type, status, balance, currency, date_opened, owner_id) "
                    "VALUES ('X', 'N', 'checking', 'active', 0, 'usd', CURRENT_DATE, :owner)"
                ),
                {"owner": DEFAULT_OWNER_ID},
            )


def test_database_refuses_a_ledger_entry_for_no_account(db_session):
    """The foreign key: history cannot exist for an account that does not."""
    with pytest.raises(IntegrityError):
        with store.transaction():
            store.record("GHOST", "deposit", Decimal("10"), "USD", Decimal("10"))


def test_adding_a_duplicate_account_number_is_refused(db_session):
    store.add(an_account("ACC-1"))

    with pytest.raises(DuplicateAccount):
        store.add(an_account("ACC-1", balance="999.00"))

    with db.session_scope():
        assert store.get("ACC-1").balance == Decimal("100.00")


# --------------------------------------------------------------------------
# locking
# --------------------------------------------------------------------------


def test_opposite_transfers_do_not_deadlock(client, make_account):
    """Two transfers in opposite directions, arriving together.

    Locking rows in the order the request happens to name them lets A→B and B→A
    each take the row the other needs. Postgres resolves that by killing one
    transaction, which surfaces as a 500 on a request that was perfectly valid.
    store.get_many_for_update() sorts first, so there is no cycle to break.
    """
    from concurrent.futures import ThreadPoolExecutor

    make_account("ACC-1", balance="500.00")
    make_account("ACC-2", balance="500.00")

    def move(i):
        source, target = ("ACC-1", "ACC-2") if i % 2 else ("ACC-2", "ACC-1")
        return client.post(
            "/transfers",
            json={
                "from_account_number": source,
                "to_account_number": target,
                "amount": "1.00",
            },
        )

    with ThreadPoolExecutor(max_workers=16) as pool:
        responses = list(pool.map(move, range(120)))

    server_errors = [r.status_code for r in responses if r.status_code >= 500]
    assert server_errors == [], f"deadlocked: {len(server_errors)} of 120 failed"

    # Equal numbers each way, so the money ends where it started.
    with db.session_scope():
        assert store.get("ACC-1").balance == Decimal("500.00")
        assert store.get("ACC-2").balance == Decimal("500.00")

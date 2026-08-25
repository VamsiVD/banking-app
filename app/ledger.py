"""In-memory transaction ledger.

Append-only: entries are written once and never edited or deleted. A correction
is a new entry in the opposite direction, not a mutation of the original — that
is the whole point of a ledger.

`record()` is implemented so the transactions router can write from day one.
Reading entries back (filtering, paging, statements) belongs in the statements
router, which owns the query side.

Shares the store lock, so a movement and its ledger entry land together inside
one `store.transaction()` block rather than as two steps a reader can see between.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app import store
from app.models import Transaction, TransactionType

_entries: list[Transaction] = []


def record(
    account_number: str,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    balance_after: Decimal,
    counterparty: str | None = None,
    description: str | None = None,
) -> Transaction:
    """Append one entry and return it.

    Call this from inside the same `store.transaction()` block that moves the
    money, so the balance and its ledger entry can never disagree:

        with store.transaction():
            account.balance += amount
            store.put(account)
            ledger.record(account.account_number, TransactionType.deposit,
                          amount, account.currency, account.balance)
    """
    entry = Transaction(
        id=uuid.uuid4().hex,
        account_number=account_number,
        type=type,
        amount=amount,
        currency=currency,
        balance_after=balance_after,
        counterparty=counterparty,
        description=description,
        timestamp=datetime.now(timezone.utc),
    )
    with store.transaction():
        _entries.append(entry)
    return entry


def for_account(account_number: str) -> list[Transaction]:
    """Every entry for one account, oldest first. Filter and page in the router."""
    with store.transaction():
        return [e for e in _entries if e.account_number == account_number]


def list_all() -> list[Transaction]:
    with store.transaction():
        return list(_entries)


def reset() -> None:
    """Empty the ledger. For tests — pair it with store.reset()."""
    with store.transaction():
        _entries.clear()

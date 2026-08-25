"""In-memory stand-in for the database: accounts and the transaction ledger.

Both live here because they share one lock — a transfer touches an account
balance and its ledger entry together, and `transaction()` is what makes that
atomic. Go through these functions rather than touching `_accounts` /
`_entries` directly. When a real database lands, this file is the only one
that has to change.
"""

import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.models import BankAccount, Transaction, TransactionType

_accounts: dict[str, BankAccount] = {}
_entries: list[Transaction] = []

# FastAPI runs sync path operations in a threadpool, so two requests really can
# interleave. Reentrant because the helpers below take it themselves and may be
# called from inside a transaction() block.
_lock = threading.RLock()


@contextmanager
def transaction() -> Iterator[None]:
    """Hold the lock across a multi-step read-modify-write.

    A transfer reads two accounts, checks a balance, then writes both back plus
    a ledger entry. Without this, a second request can land in the middle and
    overdraw the account. Single calls below are already safe on their own;
    sequences are not, so wrap them:

        with store.transaction():
            src = store.get(...)
            ...
            store.put(src)
            store.record(...)
    """
    with _lock:
        yield


# --- accounts ---


def get(account_number: str) -> BankAccount | None:
    with _lock:
        return _accounts.get(account_number)


def exists(account_number: str) -> bool:
    with _lock:
        return account_number in _accounts


def add(account: BankAccount) -> BankAccount:
    """Insert a new account. Returns None-free; caller checks `exists` first."""
    with _lock:
        _accounts[account.account_number] = account
        return account


def put(account: BankAccount) -> BankAccount:
    """Overwrite an existing account (used after mutating a balance or status)."""
    with _lock:
        _accounts[account.account_number] = account
        return account


def list_all() -> list[BankAccount]:
    """Snapshot of every account. Filtering and paging happen in the router."""
    with _lock:
        return list(_accounts.values())


# --- ledger ---
# Append-only: entries are written once and never edited or deleted. A
# correction is a new entry in the opposite direction, not a mutation of the
# original.


def record(
    account_number: str,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    balance_after: Decimal,
    counterparty: str | None = None,
    description: str | None = None,
) -> Transaction:
    """Append one ledger entry and return it. Call inside `transaction()`."""
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
    with _lock:
        _entries.append(entry)
    return entry


def for_account(account_number: str) -> list[Transaction]:
    """Every ledger entry for one account, oldest first."""
    with _lock:
        return [e for e in _entries if e.account_number == account_number]


def list_transactions() -> list[Transaction]:
    with _lock:
        return list(_entries)


def reset() -> None:
    """Empty accounts and the ledger. For tests — call between cases."""
    with _lock:
        _accounts.clear()
        _entries.clear()

"""In-memory stand-in for the database.

Scope note: this is a module-level dict. It resets on every restart and holds no
data across processes. That is deliberate for this phase — the project is
API-only right now.

Go through these functions rather than touching `_accounts` directly. When a real
database lands, this file is the only one that has to change.
"""

import threading
from contextlib import contextmanager
from collections.abc import Iterator

from app.models import BankAccount

_accounts: dict[str, BankAccount] = {}

# FastAPI runs sync path operations in a threadpool, so two requests really can
# interleave. Reentrant because the helpers below take it themselves and may be
# called from inside a transaction() block.
_lock = threading.RLock()


@contextmanager
def transaction() -> Iterator[None]:
    """Hold the store lock across a multi-step read-modify-write.

    A transfer reads two accounts, checks a balance, then writes both back. Without
    this, a second request can land between the check and the write and overdraw
    the account. Single calls below are already safe on their own; sequences are
    not, so wrap them:

        with store.transaction():
            src = store.get(...)
            ...
            store.put(src)
    """
    with _lock:
        yield


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


def reset() -> None:
    """Empty the store. For tests — call it between cases so they stay isolated."""
    with _lock:
        _accounts.clear()

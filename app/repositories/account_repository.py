"""Account access for the transfer flow.

Thin wrapper over `app.core.store`, which is where the SQL lives. Callers go
through here rather than touching `store` directly, so a change to how accounts
are fetched stays in one file.
"""

from decimal import Decimal

from app.core import store
from app.schemas.account_schema import BankAccount


def get(account_number: str) -> BankAccount | None:
    return store.get(account_number)


def get_many_for_update(account_numbers: list[str]) -> dict[str, BankAccount]:
    """Fetch and lock several accounts at once, for a caller about to write to all.

    Two `get()` calls would lock in the order the request happened to name them,
    which lets simultaneous A->B and B->A transfers deadlock. This takes them in a
    fixed order instead. See `store.get_many_for_update`.
    """
    return store.get_many_for_update(account_numbers)


def update_balance(account: BankAccount, balance: Decimal) -> BankAccount:
    """Return a copy of `account` at a new balance, and store it.

    A copy rather than an in-place `account.balance = ...` so the write goes
    through `store.put()` and there is exactly one place a balance changes.
    """
    return store.put(account.model_copy(update={"balance": balance}))

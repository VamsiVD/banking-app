"""Account access for the transfer flow.

Thin wrapper over `app.core.store`. When a real database lands, this is the file
that changes — callers never touch `store` directly.
"""

from decimal import Decimal

from app.core import store
from app.schemas.models import BankAccount


def get(account_number: str) -> BankAccount | None:
    return store.get(account_number)


def update_balance(account: BankAccount, balance: Decimal) -> BankAccount:
    """Return a copy of `account` at a new balance, and store it.

    A copy rather than an in-place `account.balance = ...` because store.get()
    hands back the live object: mutating it writes to the store whether or not
    store.put() is ever reached. Going through put() keeps the write in one
    place, which is where a real database call will eventually go.
    """
    return store.put(account.model_copy(update={"balance": balance}))

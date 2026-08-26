"""Account access for the transfer flow.

Thin wrapper over `app.core.store`, which is where the SQL lives. Callers go
through here rather than touching `store` directly, so a change to how accounts
are fetched stays in one file.
"""

from decimal import Decimal
from sqlalchemy import func, select

from app.core import store
from app.api_schemas.account_schema import BankAccount

def get_max_account_number() -> str | None:
    with store.session() as session:
        return session.scalar(
            select(func.max(AccountTable.account_number))
        )

def get(account_number: str) -> BankAccount | None:
    return store.get(account_number)


def get_many_for_update(account_numbers: list[str]) -> dict[str, BankAccount]:
    return store.get_many_for_update(account_numbers)


def get_all() -> list[BankAccount]:
    return store.list_all()


def exists(account_number: str) -> bool:
    return store.exists(account_number)


def create(account: BankAccount) -> BankAccount:
    return store.add(account)


def update_balance(account: BankAccount, balance: Decimal) -> BankAccount:
    return store.put(
        account.model_copy(update={"balance": balance})
    )


def update_status(account: BankAccount, status: str) -> BankAccount:
    return store.put(
        account.model_copy(update={"status": status})
    )


def delete(account_number: str) -> bool:
    return store.remove(account_number)
"""Transaction access for deposits and withdrawals.

Thin wrapper over app.core.store. Transaction services use this repository
instead of accessing the database layer directly.
"""

from decimal import Decimal

from app.core import store
from app.schemas.transaction_schema import Transaction, TransactionType


def create(
    account_number: str,
    transaction_type: TransactionType,
    amount: Decimal,
    currency: str,
    balance_after: Decimal,
    counterparty: str | None = None,
    description: str | None = None,
) -> Transaction:
    return store.record(
        account_number=account_number,
        type=transaction_type,
        amount=amount,
        currency=currency,
        balance_after=balance_after,
        counterparty=counterparty,
        description=description,
    )


def get_for_account(account_number: str) -> list[Transaction]:
    return store.for_account(account_number)


def get_all() -> list[Transaction]:
    return store.list_transactions()
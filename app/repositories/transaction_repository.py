"""Transaction access for deposits, withdrawals, and ledger queries.

Thin wrapper over `app.core.store`. When a real database lands, this is the
file that changes — callers never touch `store` directly.
"""

from decimal import Decimal

from app.core import store
from app.schemas.transaction_schema import Transaction, TransactionType


def add(
    account_number: str,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    balance_after: Decimal,
    counterparty: str | None = None,
    description: str | None = None,
) -> Transaction:
    """Create and store a transaction ledger entry."""
    return store.record(
        account_number=account_number,
        type=type,
        amount=amount,
        currency=currency,
        balance_after=balance_after,
        counterparty=counterparty,
        description=description,
    )


def get_for_account(account_number: str) -> list[Transaction]:
    """Return all transactions for an account."""
    return store.for_account(account_number)


def list_all() -> list[Transaction]:
    """Return all transactions."""
    return store.list_transactions()
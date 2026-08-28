"""Transaction history and statements.

    GET /accounts/{account_number}/statement      summary over a period:
                                                    opening/closing balance,
                                                    totals in and out, entry count

Read-only against the same ledger `app/core/store.py` writes — never appends
here, since writing is the transactions router's job and the ledger is
append-only besides.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.core import store
from app.core.auth_guard import get_current_principal
from app.errors import AccountNotFound
from app.api_schemas.statement_schema import AccountStatement
from app.api_schemas.transaction_schema import Transaction, TransactionType

router = APIRouter(prefix="/accounts", tags=["statements"])

# What counts as money coming in, for both the totals and reconstructing the
# opening balance below.
_INFLOWS = {TransactionType.deposit, TransactionType.transfer_in}


def _signed(entry: Transaction) -> Decimal:
    return entry.amount if entry.type in _INFLOWS else -entry.amount


@router.get("/{account_number}/statement", response_model=AccountStatement)
def get_statement(
    account_number: str,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    caller=Depends(get_current_principal),
) -> AccountStatement:
    account = store.get(account_number)
    if account is None:
        raise AccountNotFound(f"No account with number {account_number!r}.")

    # Oldest first, so the first/last entries in range double as the period's
    # opening/closing points.
    entries = [
        entry
        for entry in store.for_account(account_number)
        if (from_date is None or entry.timestamp.date() >= from_date)
        and (to_date is None or entry.timestamp.date() <= to_date)
    ]

    if entries:
        # No entry records the balance *before* it landed, only after — so the
        # opening balance is the first entry's balance_after, undone.
        opening_balance = entries[0].balance_after - _signed(entries[0])
        closing_balance = entries[-1].balance_after
    else:
        # No history in range is a real, valid statement (a 200, not a 404) —
        # nothing moved, so opening and closing are just the current balance.
        opening_balance = closing_balance = account.balance

    total_in = sum((e.amount for e in entries if e.type in _INFLOWS), Decimal("0"))
    total_out = sum((e.amount for e in entries if e.type not in _INFLOWS), Decimal("0"))

    return AccountStatement(
        account_number=account_number,
        currency=account.currency,
        period_start=from_date,
        period_end=to_date,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        total_in=total_in,
        total_out=total_out,
        entry_count=len(entries),
    )

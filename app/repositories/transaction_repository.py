"""Transaction access for deposits and withdrawals.

Thin wrapper over `app.core.store`. Services use this repository instead of
reaching into the database layer themselves.

The transfer queries at the bottom are the exception: they are written as SQL
against the session rather than routed through `store`, because filtering,
ordering and paging belong in the database. `core/store.py`'s own docstring
says so — pulling every row back with `list_transactions()` and slicing it in
Python is the thing it tells you not to do.
"""

from decimal import Decimal

from sqlalchemy import func, or_, select

from app.core import store
from app.db import current_session
from app.api_schemas.transaction_schema import Transaction, TransactionType
from app.api_schemas.transfer_schema import TransferSummary
from app.sql_schemas.tables import TransactionRow


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


# --- transfers ---
# A transfer is read back from its `transfer_out` row, which already records both
# sides: `account_number` paid, `counterparty` was paid. The matching
# `transfer_in` row would only repeat it from the other direction.


def _to_summary(row: TransactionRow) -> TransferSummary:
    return TransferSummary(
        id=row.id,
        from_account_number=row.account_number,
        to_account_number=row.counterparty,
        amount=row.amount,
        currency=row.currency,
        description=row.description,
        timestamp=row.timestamp,
    )


def _transfers_out():
    """Base query: the debit side of every transfer."""
    return select(TransactionRow).where(
        TransactionRow.type == TransactionType.transfer_out
    )


def count_transfers(account_number: str | None = None) -> int:
    """How many transfers match, ignoring paging.

    Counted in SQL rather than by measuring a fetched list, so `total` stays
    right no matter what `limit` was asked for.
    """
    stmt = select(func.count()).select_from(TransactionRow).where(
        TransactionRow.type == TransactionType.transfer_out
    )
    if account_number is not None:
        stmt = stmt.where(_involves(account_number))
    return current_session().scalar(stmt) or 0


def _involves(account_number: str):
    """Matches a transfer with this account on either side.

    A transfer is as much yours when you received it as when you sent it, so
    filtering by account has to look at the counterparty too.
    """
    return or_(
        TransactionRow.account_number == account_number,
        TransactionRow.counterparty == account_number,
    )


def list_transfers(
    account_number: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TransferSummary]:
    """A page of transfers, newest first.

    Newest first because that is what anyone looking at a transfer list wants;
    the ledger itself hands entries back oldest-first, which suits a statement
    and not this. The id tiebreak keeps the order stable between calls when two
    transfers share a timestamp.
    """
    stmt = _transfers_out()
    if account_number is not None:
        stmt = stmt.where(_involves(account_number))
    stmt = (
        stmt.order_by(TransactionRow.timestamp.desc(), TransactionRow.id.desc())
        .limit(limit)
        .offset(offset)
        .execution_options(populate_existing=True)
    )
    return [_to_summary(row) for row in current_session().scalars(stmt)]


def get_transfer(transfer_id: str) -> TransferSummary | None:
    """One transfer by the id of its debit entry, or None.

    The `type` filter is what makes a deposit's id miss here rather than come
    back as a transfer with a null destination.
    """
    stmt = (
        _transfers_out()
        .where(TransactionRow.id == transfer_id)
        .execution_options(populate_existing=True)
    )
    row = current_session().scalars(stmt).one_or_none()
    return _to_summary(row) if row is not None else None


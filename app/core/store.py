"""Accounts and the transaction ledger, backed by PostgreSQL.

Both live here because they share one transaction — a transfer touches an account
balance and its ledger entry together, and `transaction()` is what makes that
atomic. Go through these functions rather than writing SQL in a router or a
service; when the schema changes, this file and `tables.py` are the only ones
that have to.

Every function below has the same name, arguments and return type it had when
this was a dict and a list. `get()` still hands back a Pydantic `BankAccount`,
never a SQLAlchemy row, so nothing above this line had to change.

Two things really did change, both improvements:

  - `transaction()` is now a database transaction. It used to be a mutex, which
    meant a failure halfway through a transfer left the money where it fell.
    Now the work rolls back.
  - `get()` inside a `transaction()` block takes a real row lock (SELECT ... FOR
    UPDATE) instead of a Python one. The old lock only protected a single
    process, so it was already a fiction under `uvicorn --workers 4`.

If you need a query these cannot express — filtering, sorting, paging — take the
session with `Depends(db.get_session)` and write it properly. Do not fetch every
row with `list_all()` and loop in Python.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db import current_session, in_transaction
from app.db import transaction as _transaction
from app.errors import AccountHasHistory, DuplicateAccount
from app.api_schemas.account_schema import BankAccount
from app.api_schemas.transaction_schema import Transaction, TransactionType
from app.sql_schemas.tables import AccountRow, TransactionRow

def get_next_account_number() -> str:
    accounts = list_all()

    if not accounts:
        return "100"

    max_number = max(int(account.account_number) for account in accounts)

    return str(max_number + 1)

@contextmanager
def transaction() -> Iterator[None]:
    """Hold a database transaction across a multi-step read-modify-write.

    A transfer reads two accounts, checks a balance, then writes both back plus
    a ledger entry. Wrap that sequence:

        with store.transaction():
            src = store.get(...)
            ...
            store.put(src)
            store.record(...)

    Inside the block, `get()` locks the rows it returns and they stay locked
    until the block ends, so nothing can slip between the check and the write.
    The block commits when it exits cleanly and rolls back if anything raises.

    Reentrant: nesting these joins the outer one rather than starting a second.
    Single calls below open their own block when they are not already inside one,
    so they are safe on their own; sequences are not.
    """
    with _transaction():
        yield


# --- accounts ---


def _to_account(row: AccountRow) -> BankAccount:
    """Row -> Pydantic. The boundary the rest of the app never sees past."""
    return BankAccount(
        account_number=row.account_number,
        account_holder_name=row.account_holder_name,
        account_type=row.account_type,
        status=row.status,
        balance=row.balance,
        currency=row.currency,
        date_opened=row.date_opened,
        owner_id=row.owner_id,
    )


def get(account_number: str) -> BankAccount | None:
    session = current_session()
    stmt = (
        select(AccountRow)
        .where(AccountRow.account_number == account_number)
        # Without this, a row already in this session's identity map comes back
        # with the values it had when first loaded, however long ago that was.
        .execution_options(populate_existing=True)
    )
    if in_transaction():
        # About to be written, so lock it for the rest of the block.
        stmt = stmt.with_for_update()
    row = session.scalars(stmt).one_or_none()
    return _to_account(row) if row is not None else None


def get_many_for_update(account_numbers: list[str]) -> dict[str, BankAccount]:
    """Lock several accounts at once, in a fixed order. Returns those that exist.

    Locking in the order the caller happened to name them is how a deadlock
    happens: two simultaneous transfers, A->B and B->A, each take one row and
    then wait forever for the other. Postgres notices and kills one of them,
    which the client sees as a 500 on a request that was perfectly valid.

    Sorting first removes the cycle — every caller takes the same rows in the
    same order, so one simply waits for the other. Call this instead of two
    separate `get()`s whenever you are about to write to both.
    """
    if not account_numbers:
        return {}

    session = current_session()
    ordered = sorted(set(account_numbers))
    stmt = (
        select(AccountRow)
        .where(AccountRow.account_number.in_(ordered))
        # Postgres locks rows in the order the scan returns them, not the order in
        # the IN clause, so the ORDER BY is what actually makes this deterministic.
        .order_by(AccountRow.account_number)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {row.account_number: _to_account(row) for row in session.scalars(stmt)}


def exists(account_number: str) -> bool:
    session = current_session()
    stmt = select(AccountRow.account_number).where(
        AccountRow.account_number == account_number
    )
    return session.scalar(stmt) is not None


def add(account: BankAccount) -> BankAccount:
    """Insert a new account.

    Raises DuplicateAccount if the number is taken. The dict version silently
    overwrote, which meant two concurrent creates quietly destroyed one account;
    the primary key now catches that even when two processes race past the same
    `exists()` check.
    """
    with transaction():
        session = current_session()
        session.add(AccountRow(**account.model_dump()))
        try:
            # Flush inside the block so the constraint violation surfaces here,
            # attributable to this call, rather than at commit time somewhere else.
            session.flush()
        except IntegrityError as exc:
            raise DuplicateAccount(
                f"An account numbered {account.account_number!r} already exists."
            ) from exc
    return account


def put(account: BankAccount) -> BankAccount:
    """Write an account back after changing a balance or a status.

    Insert-or-update, matching what assigning into the old dict did.
    """
    with transaction():
        session = current_session()
        session.merge(AccountRow(**account.model_dump()))
        session.flush()
    return account


def remove(account_number: str) -> bool:
    """Delete an account. True if there was one to delete.

    Refuses once the account has ledger history. The foreign key from
    `transactions` would reject it anyway, but an IntegrityError surfacing three
    layers up is a worse answer than a named one — and history is the point of a
    ledger. Closing an account is `status = "closed"`, not a delete.
    """
    with transaction():
        session = current_session()
        row = session.get(AccountRow, account_number)
        if row is None:
            return False

        has_history = session.scalar(
            select(TransactionRow.id)
            .where(TransactionRow.account_number == account_number)
            .limit(1)
        )
        if has_history is not None:
            raise AccountHasHistory(
                f"Account {account_number!r} has ledger entries and cannot be "
                "deleted. Set its status to 'closed' instead."
            )

        session.delete(row)
        session.flush()
        return True


def list_all() -> list[BankAccount]:
    """Every account, by account number. Filtering and paging happen in the router.

    Ordered explicitly because a table has no natural order — without ORDER BY,
    Postgres may return rows in whatever sequence it finds them, and that changes
    as rows are updated.
    """
    session = current_session()
    stmt = (
        select(AccountRow)
        .order_by(AccountRow.account_number)
        .execution_options(populate_existing=True)
    )
    return [_to_account(row) for row in session.scalars(stmt)]


# --- ledger ---
# Append-only: entries are written once and never edited or deleted. A
# correction is a new entry in the opposite direction, not a mutation of the
# original. The rule is enforced by omission — one writer, three readers, and
# nothing that updates.


def _to_transaction(row: TransactionRow) -> Transaction:
    return Transaction(
        id=row.id,
        account_number=row.account_number,
        type=row.type,
        amount=row.amount,
        currency=row.currency,
        balance_after=row.balance_after,
        counterparty=row.counterparty,
        description=row.description,
        timestamp=row.timestamp,
    )


def record(
    account_number: str,
    type: TransactionType,
    amount: Decimal,
    currency: str,
    balance_after: Decimal,
    counterparty: str | None = None,
    description: str | None = None,
) -> Transaction:
    """Append one ledger entry and return it. Call inside `transaction()`.

    Written in the same block that moves the money, so a balance and its history
    can never disagree. That used to be a shared mutex and a promise; it is now
    the same database transaction.
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
    with transaction():
        session = current_session()
        session.add(TransactionRow(**entry.model_dump()))
        session.flush()
    return entry


def for_account(account_number: str) -> list[Transaction]:
    """Every ledger entry for one account, oldest first."""
    session = current_session()
    stmt = (
        select(TransactionRow)
        .where(TransactionRow.account_number == account_number)
        # Both sides of a transfer are written microseconds apart and can share a
        # timestamp; the id tiebreak keeps the order stable between calls.
        .order_by(TransactionRow.timestamp, TransactionRow.id)
        .execution_options(populate_existing=True)
    )
    return [_to_transaction(row) for row in session.scalars(stmt)]


def list_transactions() -> list[Transaction]:
    session = current_session()
    stmt = (
        select(TransactionRow)
        .order_by(TransactionRow.timestamp, TransactionRow.id)
        .execution_options(populate_existing=True)
    )
    return [_to_transaction(row) for row in session.scalars(stmt)]


def reset() -> None:
    """Empty accounts, the ledger and users. For tests — call between cases.

    TRUNCATE rather than DELETE because it does not scan the tables, and all three
    together because the foreign key means transactions cannot outlive accounts.
    """
    with transaction():
        current_session().execute(
            text(
                "TRUNCATE TABLE transactions, subscriptions, accounts, users "
                "RESTART IDENTITY CASCADE"
            )
        )

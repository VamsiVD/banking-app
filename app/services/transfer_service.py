"""Transfers — moving funds between two accounts.

Owner: utoker
Branch: feat/transfers

Deposits and withdrawals are a separate slice; see routers/transactions.py.

Validation fully precedes mutation here. That was originally because
`store.transaction()` was a mutex with no way to undo a half-applied transfer;
it is now a real database transaction that rolls back, so the ordering is no
longer load-bearing. It stays anyway — refusing before touching either balance
is easier to read than trusting the rollback.
"""

from app.core import store, transfer_rules
from app.errors import AccountNotFound
from app.schemas.transaction_schema import TransactionType
from app.repositories import account_repository
from app.schemas.transfer_schema import TransferRequest, TransferResult


def _active_account(account_number: str, account):
    """Check an already-locked account may move money, or raise.

    Takes the account rather than fetching it, because both rows have to be
    locked together — see the call site.
    """
    if account is None:
        raise AccountNotFound(f"No account with number {account_number!r}.")
    transfer_rules.assert_active(account)
    return account


def execute_transfer(body: TransferRequest) -> TransferResult:
    with store.transaction():
        # Both rows in one locking read, taken in sorted order. Fetching them one
        # at a time in the order the request named them lets two opposite
        # transfers — A→B and B→A, arriving together — each hold the row the other
        # needs. Postgres breaks that deadlock by killing one of them, so a
        # perfectly valid transfer fails with a 500.
        locked = account_repository.get_many_for_update(
            [body.from_account_number, body.to_account_number]
        )
        source = _active_account(
            body.from_account_number, locked.get(body.from_account_number)
        )
        destination = _active_account(
            body.to_account_number, locked.get(body.to_account_number)
        )

        transfer_rules.assert_same_currency(source, destination)
        transfer_rules.assert_sufficient_funds(source, body.amount)

        # Every refusal is now behind us, so both sides can be written.
        source = account_repository.update_balance(source, source.balance - body.amount)
        destination = account_repository.update_balance(
            destination, destination.balance + body.amount
        )

        debit = store.record(
            source.account_number,
            TransactionType.transfer_out,
            body.amount,
            source.currency,
            source.balance,
            counterparty=destination.account_number,
            description=body.description,
        )
        credit = store.record(
            destination.account_number,
            TransactionType.transfer_in,
            body.amount,
            destination.currency,
            destination.balance,
            counterparty=source.account_number,
            description=body.description,
        )
        return TransferResult(debit=debit, credit=credit)

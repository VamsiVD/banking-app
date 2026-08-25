"""Transfers — moving funds between two accounts.

Owner: utoker
Branch: feat/transfers

Deposits and withdrawals are a separate slice; see routers/transactions.py.

Validation fully precedes mutation here. `store.transaction()` is a lock, not a
rollback, so a half-applied transfer could not be undone — every reason to
refuse is ruled out before either balance is written.
"""

from app.core import store, transfer_rules
from app.errors import AccountNotFound
from app.schemas.models import TransactionType
from app.repositories import account_repository
from app.schemas.transfer_schema import TransferRequest, TransferResult


def _active_account(account_number: str):
    account = account_repository.get(account_number)
    if account is None:
        raise AccountNotFound(f"No account with number {account_number!r}.")
    transfer_rules.assert_active(account)
    return account


def execute_transfer(body: TransferRequest) -> TransferResult:
    with store.transaction():
        source = _active_account(body.from_account_number)
        destination = _active_account(body.to_account_number)

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

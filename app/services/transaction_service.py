"""Deposits and withdrawals — moving funds into or out of one account.

Deposits and withdrawals are separate from transfers. This service contains
the business logic; the router only handles the HTTP request.
"""

from app.core import store
from app.errors import AccountNotActive, AccountNotFound, InsufficientFunds
from app.repositories import account_repository, transaction_repository
from app.api_schemas.account_schema import AccountStatus
from app.api_schemas.transaction_schema import MoneyMovement, TransactionType


def _active_account(account_number: str):
    account = account_repository.get(account_number)

    if account is None:
        raise AccountNotFound(
            f"No account with number {account_number!r}."
        )

    if account.status is not AccountStatus.active:
        raise AccountNotActive(
            f"Account {account.account_number!r} is "
            f"{account.status.value}; only active accounts can move money."
        )

    return account


def deposit(account_number: str, movement: MoneyMovement):
    with store.transaction():
        account = _active_account(account_number)

        account = account_repository.update_balance(
            account,
            account.balance + movement.amount,
        )

        return transaction_repository.create(
            account.account_number,
            TransactionType.deposit,
            movement.amount,
            account.currency,
            account.balance,
            description=movement.description,
        )


def withdraw(account_number: str, movement: MoneyMovement):
    with store.transaction():
        account = _active_account(account_number)

        if account.balance < movement.amount:
            raise InsufficientFunds(
                f"Account {account.account_number!r} holds "
                f"{account.balance} {account.currency}; "
                f"cannot withdraw {movement.amount}."
            )

        account = account_repository.update_balance(
            account,
            account.balance - movement.amount,
        )

        return transaction_repository.create(
            account.account_number,
            TransactionType.withdrawal,
            movement.amount,
            account.currency,
            account.balance,
            description=movement.description,
        )
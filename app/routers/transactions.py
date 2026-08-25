"""Money movement — deposits and withdrawals.

Owner: utoker
Branch: feat/transactions

Endpoints:
    POST /accounts/{account_number}/deposit
    POST /accounts/{account_number}/withdraw
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter

from app import ledger, store
from app.errors import AccountNotActive, AccountNotFound, InsufficientFunds
from app.models import (
    AccountStatus,
    AccountType,
    BankAccount,
    MoneyMovement,
    TransactionType,
)
from app.routers.BankProfile import accounts as profile_accounts


router = APIRouter(tags=["transactions"])


def load_accounts():
    """Load the sample accounts from BankProfile into the shared store."""

    if store.list_all():
        return

    for account in profile_accounts:
        bank_account = BankAccount(
            account_number=account["account_number"],
            account_holder_name=account["account_holder_name"],
            account_type=AccountType(account["account_type"]),
            status=AccountStatus(account["status"]),
            balance=Decimal(str(account["balance"])),
            currency=account["currency"],
            date_opened=date.fromisoformat(account["date_opened"]),
        )

        store.add(bank_account)


load_accounts()


@router.post("/accounts/{account_number}/deposit")
def deposit(account_number: str, movement: MoneyMovement):

    with store.transaction():
        account = store.get(account_number)

        if account is None:
            raise AccountNotFound(
                f"No account with number {account_number!r}."
            )

        if account.status is not AccountStatus.active:
            raise AccountNotActive(
                f"Account {account_number!r} is not active."
            )

        account = account.model_copy(
            update={
                "balance": account.balance + movement.amount
            }
        )

        store.put(account)

        transaction = ledger.record(
            account_number=account.account_number,
            type=TransactionType.deposit,
            amount=movement.amount,
            currency=account.currency,
            balance_after=account.balance,
            description=movement.description,
        )

    return {
        "account": account,
        "transaction": transaction,
    }


@router.post("/accounts/{account_number}/withdraw")
def withdraw(account_number: str, movement: MoneyMovement):

    with store.transaction():
        account = store.get(account_number)

        if account is None:
            raise AccountNotFound(
                f"No account with number {account_number!r}."
            )

        if account.status is not AccountStatus.active:
            raise AccountNotActive(
                f"Account {account_number!r} is not active."
            )

        if movement.amount > account.balance:
            raise InsufficientFunds(
                f"Account {account_number!r} has insufficient funds."
            )

        account = account.model_copy(
            update={
                "balance": account.balance - movement.amount
            }
        )

        store.put(account)

        transaction = ledger.record(
            account_number=account.account_number,
            type=TransactionType.withdrawal,
            amount=movement.amount,
            currency=account.currency,
            balance_after=account.balance,
            description=movement.description,
        )

    return {
        "account": account,
        "transaction": transaction,
    }
"""Money movement — deposits and withdrawals.

Owner: utoker
Branch: feat/transactions

Endpoints:
    POST /accounts/{account_number}/deposit
    POST /accounts/{account_number}/withdraw
"""

from fastapi import APIRouter, HTTPException

from app import ledger, store
from app.models import TransactionType
from app.schemas.transaction_schema import MoneyMovement


router = APIRouter(tags=["transactions"])


@router.post("/accounts/{account_number}/deposit")
def deposit(account_number: str, movement: MoneyMovement):
    """Add funds to an active account."""

    with store.transaction():
        account = store.get(account_number)

        if account is None:
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )

        if account.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Account is not active"
            )

        account.balance += movement.amount
        store.put(account)

        transaction = store.record(
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
    """Remove funds from an active account."""

    with store.transaction():
        account = store.get(account_number)

        if account is None:
            raise HTTPException(
                status_code=404,
                detail="Account not found"
            )

        if account.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Account is not active"
            )

        if movement.amount > account.balance:
            raise HTTPException(
                status_code=409,
                detail="Insufficient funds"
            )

        account.balance -= movement.amount
        store.put(account)

        transaction = store.record(
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
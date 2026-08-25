"""Money movement — deposits, withdrawals, transfers.

Owner: utoker
Branch: feat/transactions

Endpoints to build here:
    POST /accounts/{account_number}/deposit    add funds
    POST /accounts/{account_number}/withdraw   remove funds
    POST /transfers                            move funds between two accounts

Notes:
  - Amounts are Decimal and strictly positive (models.PositiveMoney). A zero or
    negative deposit is a validation error, not a no-op.
  - Only `active` accounts move money. Anything else is AccountNotActive (409).
  - Overdrawing is InsufficientFunds (409).
  - A transfer between different currencies is CurrencyMismatch (409) — this API
    does no FX conversion.
  - A transfer to and from the same account should be rejected, not silently
    succeed as a no-op.

  - Wrap every read-modify-write in `with store.transaction():`. A transfer
    touches two accounts and must not interleave with another request.
  - Write a ledger entry for every movement, inside that same block, so a balance
    and its history can never disagree.
"""

from fastapi import APIRouter, HTTPException

from app import ledger, store
from app.models import MoneyMovement, TransactionType


router = APIRouter(tags=["transactions"])


@router.post("/accounts/{account_number}/deposit")
def deposit(account_number: str, movement: MoneyMovement):

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
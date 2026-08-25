from fastapi import APIRouter

from app.schemas.transaction_schema import MoneyMovement


router = APIRouter(tags=["transactions"])


@router.post(
    "/accounts/{account_number}/deposit",
    summary="Deposit",
    description="Add funds to an active account.",
)
def deposit(account_number: str, movement: MoneyMovement):
    return {
        "account_number": account_number,
        "amount": movement.amount,
        "description": movement.description,
    }


@router.post(
    "/accounts/{account_number}/withdraw",
    summary="Withdraw",
    description="Remove funds from an active account.",
)
def withdraw(account_number: str, movement: MoneyMovement):
    return {
        "account_number": account_number,
        "amount": movement.amount,
        "description": movement.description,
    }
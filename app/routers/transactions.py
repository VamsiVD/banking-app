from fastapi import APIRouter

from app.schemas.transaction_schema import MoneyMovement


router = APIRouter(tags=["transactions"])


@router.post("/accounts/{account_number}/deposit")
def deposit(account_number: str, movement: MoneyMovement):
    return {
        "account_number": account_number,
        "amount": movement.amount,
        "description": movement.description,
    }


@router.post("/accounts/{account_number}/withdraw")
def withdraw(account_number: str, movement: MoneyMovement):
    return {
        "account_number": account_number,
        "amount": movement.amount,
        "description": movement.description,
    }
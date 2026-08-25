from fastapi import APIRouter

from app.schemas.transaction_schema import MoneyMovement, Transaction
from app.services import transaction_service


router = APIRouter(tags=["transactions"])


@router.post(
    "/accounts/{account_number}/deposit",
    response_model=Transaction,
    summary="Deposit funds into an account",
)
def deposit(account_number: str, movement: MoneyMovement) -> Transaction:
    return transaction_service.deposit(account_number, movement)


@router.post(
    "/accounts/{account_number}/withdraw",
    response_model=Transaction,
    summary="Withdraw funds from an account",
)
def withdraw(account_number: str, movement: MoneyMovement) -> Transaction:
    return transaction_service.withdraw(account_number, movement)

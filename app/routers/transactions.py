from fastapi import APIRouter, Depends

from app.api_schemas.transaction_schema import MoneyMovement, Transaction
from app.core.auth_guard import get_current_user
from app.services import transaction_service


router = APIRouter(tags=["transactions"])


@router.post(
    "/accounts/{account_number}/deposit",
    response_model=Transaction,
    status_code=200,
    summary="Deposit funds into an account",
)
def deposit(
    account_number: str,
    movement: MoneyMovement,
    user=Depends(get_current_user),
) -> Transaction:
    return transaction_service.deposit(account_number, movement)


@router.post(
    "/accounts/{account_number}/withdraw",
    response_model=Transaction,
    status_code=200,
    summary="Withdraw funds from an account",
)
def withdraw(
    account_number: str,
    movement: MoneyMovement,
    user=Depends(get_current_user),
) -> Transaction:
    return transaction_service.withdraw(account_number, movement)
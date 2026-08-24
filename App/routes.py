from fastapi import APIRouter, HTTPException
from .schemas import BankAccountCreate
from .data import accounts


router = APIRouter()


@router.get("/accounts")
def get_accounts():
    return accounts


@router.get("/accounts/{account_number}")
def get_account(account_number: str):
    for account in accounts:
        if account["account_number"] == account_number:
            return account

    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )


@router.post("/accounts", status_code=201)
def create_account(account: BankAccountCreate):

    for existing_account in accounts:
        if existing_account["account_number"] == account.account_number:
            raise HTTPException(
                status_code=409,
                detail="Account number already exists"
            )

    new_account = account.model_dump(mode="json")
    accounts.append(new_account)

    return new_account


@router.put("/accounts/{account_number}")
def update_account(
    account_number: str,
    updated_account: BankAccountCreate
):
    for index, account in enumerate(accounts):
        if account["account_number"] == account_number:

            updated_account.account_number = account_number

            accounts[index] = updated_account.model_dump(mode="json")

            return accounts[index]

    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )


@router.delete("/accounts/{account_number}")
def delete_account(account_number: str):

    for index, account in enumerate(accounts):
        if account["account_number"] == account_number:

            deleted_account = accounts.pop(index)

            return {
                "message": "Account deleted successfully",
                "account": deleted_account
            }

    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )
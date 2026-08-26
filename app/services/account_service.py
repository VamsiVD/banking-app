from datetime import date

from app.repositories import account_repository
from app.schemas.account_schema import (
    AccountStatus,
    BankAccount,
    BankAccountCreate,
)

def get_all_accounts() -> list[BankAccount]:
    return account_repository.get_all()

def get_account_by_id(account_number: str) -> BankAccount:
    return account_repository.get(account_number)

def create_account(data: BankAccountCreate) -> BankAccount:
    if account_repository.exists(data.account_number):
        raise ValueError("Account already exists")

    account = BankAccount(
        account_number=data.account_number,
        account_holder_name=data.account_holder_name,
        account_type=data.account_type,
        status=data.status,
        balance=data.balance,
        currency=data.currency,
        date_opened=data.date_opened or date.today(),
        owner_id=data.owner_id,
    )

    return account_repository.create(account)

def update_account_status(
    account_number: str,
    status: AccountStatus
) -> BankAccount | None:
    account = account_repository.get(account_number)

    if account is None:
        return None

    return account_repository.update_status(account, status)


def delete_account(account_number: str) -> bool:
    return account_repository.delete(account_number)
"""Account profiles — create, fetch, list, change status, delete.

Reads and writes `app.core.store`, the same store every other slice uses. It
used to keep its own private list of dicts with a weaker ad-hoc schema
(float balance, raw string status), which meant an account created here was
invisible to deposits, withdrawals, and transfers (they all read `store` and
found nothing), and let a client PATCH in a status that was not a real
AccountStatus value.
"""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.core import store
from app.core.auth_guard import get_current_admin, get_current_principal
from app.errors import AccountNotFound, UserNotFound
from app.repositories.user_repository import user_repository
from app.api_schemas.account_schema import AccountStatus, BankAccount, BankAccountCreate

router = APIRouter(prefix="/accounts", tags=["Bank Profile"])


class BankAccountUpdate(BaseModel):
    """Body for a status change. The only field a PATCH may touch."""

    model_config = ConfigDict(extra="forbid")

    status: AccountStatus


def _require(account_number: str) -> BankAccount:
    account = store.get(account_number)
    if account is None:
        raise AccountNotFound(f"No account with number {account_number!r}.")
    return account


# Read
@router.get("/", response_model=list[BankAccount])
def return_all_accounts(caller=Depends(get_current_principal)) -> list[BankAccount]:
    return store.list_all()


@router.get("/{account_number}", response_model=BankAccount)
def get_account(account_number: str, caller=Depends(get_current_principal)) -> BankAccount:
    return _require(account_number)


# Create
@router.post("/", response_model=BankAccount, status_code=201)
def create_account(account: BankAccountCreate, caller=Depends(get_current_principal)) -> BankAccount:
    """Open an account with an automatically generated account number."""

    if user_repository.get_by_email(account.owner_id) is None:
        raise UserNotFound(f"No user with id {account.owner_id!r}.")

    account_number = store.get_next_account_number()

    return store.add(
        BankAccount(
            account_number=account_number,
            **account.model_dump(exclude={"date_opened"}),
            date_opened=account.date_opened or date.today(),
        )
    )


# Update
@router.patch("/{account_number}", response_model=BankAccount)
def update_account(
    account_number: str,
    update: BankAccountUpdate,
    _admin=Depends(get_current_admin),
) -> BankAccount:
    """Change an account's status. Administrators only.

    Freezing or closing an account is a decision about someone else's money, so
    a customer's own token is not enough here even though it reaches the reads.
    """
    with store.transaction():
        account = _require(account_number)
        return store.put(account.model_copy(update={"status": update.status}))


# Delete
@router.delete("/{account_number}")
def delete_account(account_number: str, _admin=Depends(get_current_admin)) -> dict[str, str]:
    """Delete an account that has no ledger history. Administrators only.

    Once money has moved, `store.remove()` refuses; deleting the account would
    orphan its entries, and an auditable ledger is the point. Close it with
    `PATCH {"status": "closed"}` instead.
    """
    if not store.remove(account_number):
        raise AccountNotFound(f"No account with number {account_number!r}.")
    return {"message": f"Account {account_number} deleted"}

"""Account profiles — create, fetch, list, change status, delete.

Reads and writes the shared store, so these endpoints and
`/accounts/{n}/deposit` now see the same accounts. They used to disagree: this
file kept its own list of five dicts with float balances, so `GET /accounts/1001`
answered 1500.0 while a deposit against the same account answered 1510.00.

The demo accounts moved to `scripts/seed.py`. Run it once after migrating:

    python -m scripts.seed

Request and response shapes come from `app.schemas.account_schema`, which mirrors
BankingApp.json — including `Decimal` balances, because floats lose cents.
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core import store
from app.errors import AccountNotFound
from app.schemas.account_schema import BankAccountCreate, BankAccountResponse
from app.schemas.account_schema import AccountStatus, BankAccount

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
@router.get("/", response_model=list[BankAccountResponse])
def return_all_accounts() -> list[BankAccount]:
    return store.list_all()


@router.get("/{account_number}", response_model=BankAccountResponse)
def get_account(account_number: str) -> BankAccount:
    return _require(account_number)


# Create
@router.post("/", response_model=BankAccountResponse, status_code=201)
def create_account(account: BankAccountCreate) -> BankAccount:
    """Open an account.

    The account number comes from the request body, as BankingApp.json specifies.
    It used to be generated as `str(1000 + len(accounts) + 1)`, which reuses a
    number as soon as anything is deleted; the primary key now refuses a
    duplicate outright and `store.add()` reports it as a 409.
    """
    from datetime import date

    return store.add(
        BankAccount(
            **account.model_dump(exclude={"date_opened"}),
            # Optional on the way in, always set once stored.
            date_opened=account.date_opened or date.today(),
        )
    )


# Update
@router.patch("/{account_number}", response_model=BankAccountResponse)
def update_account(account_number: str, update: BankAccountUpdate) -> BankAccount:
    with store.transaction():
        account = _require(account_number)
        return store.put(account.model_copy(update={"status": update.status}))


# Delete
@router.delete("/{account_number}")
def delete_account(account_number: str) -> dict[str, str]:
    """Delete an account that has no ledger history.

    Once money has moved, `store.remove()` refuses — deleting the account would
    orphan its entries, and an auditable ledger is the point. Close it with
    `PATCH {"status": "closed"}` instead.
    """
    if not store.remove(account_number):
        raise AccountNotFound(f"No account with number {account_number!r}.")
    return {"message": f"Account {account_number} deleted"}

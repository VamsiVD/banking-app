# Bank Profile - Accounts
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

class BankAccountCreate(BaseModel):
    account_holder_name: str
    account_type: str
    balance: float
    currency: str

class BankAccountUpdate(BaseModel):
    status: str

router = APIRouter(
    prefix="/accounts",
    tags=["Bank Profile"]
)

# Data - Accounts
accounts = [
    {
        "account_number": "1001",
        "account_holder_name": "Sana Smith",
        "account_type": "savings",
        "balance": 1500.0,
        "currency": "USD",
        "date_opened": "2026-08-25",
        "status": "active"
    },
{
        "account_number": "1002",
        "account_holder_name": "Alex Walker",
        "account_type": "checking",
        "balance": 800.0,
        "currency": "USD",
        "date_opened": "2026-08-25",
        "status": "active"
    },
    {
        "account_number": "1003",
        "account_holder_name": "Ria Sen",
        "account_type": "business",
        "balance": 5200.0,
        "currency": "USD",
        "date_opened": "2026-08-20",
        "status": "active"
    },
{
        "account_number": "1004",
        "account_holder_name": "Dylan Sharma",
        "account_type": "fixed_deposit",
        "balance": 10000.0,
        "currency": "USD",
        "date_opened": "2026-08-18",
        "status": "inactive"
    },
    {
        "account_number": "1005",
        "account_holder_name": "Rinal Das",
        "account_type": "checking",
        "balance": 250.0,
        "currency": "USD",
        "date_opened": "2026-08-15",
        "status": "frozen"
    }
]

# Read
@router.get("/")
def return_all_accounts():
    return accounts

@router.get("/{account_number}")
def get_account(account_number: str):
    for account in accounts:
        if account["account_number"] == account_number:
            return account
    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )

# Create
@router.post("/")
def create_account(account: BankAccountCreate):
    new_account = {
        "account_number": str(1000 + len(accounts) + 1),
        "account_holder_name": account.account_holder_name,
        "account_type": account.account_type,
        "balance": account.balance,
        "currency": account.currency,
        "date_opened": "2026-08-25",
        "status": "active"
    }

    accounts.append(new_account)

    return new_account

# Update
@router.patch("/{account_number}")
def update_account(account_number: str, update: BankAccountUpdate):
    for account in accounts:
        if account["account_number"] == account_number:
            account["status"] = update.status
            return account
    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )

# Delete
@router.delete("/{account_number}")
def delete_account(account_number: str):
    for account in accounts:
        if account["account_number"] == account_number:
            accounts.remove(account)
            return {"message": f"Account {account_number} deleted"}
    raise HTTPException(
        status_code=404,
        detail="Account not found"
    )
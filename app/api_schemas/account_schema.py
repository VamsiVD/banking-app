"""Account domain: types, create request, and stored/returned shape.

`BankAccountCreate` is a direct translation of BankingApp.json; that file is
the contract, so keep the two in step. If you need a field the schema does
not have, change the schema in the same PR.
"""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.api_schemas.primitives import AccountNumber, Currency, Money, UserId


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    business = "business"
    fixed_deposit = "fixed_deposit"


class AccountStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    frozen = "frozen"
    closed = "closed"


class BankAccountCreate(BaseModel):
    """Request body for creating an account."""

    model_config = ConfigDict(extra="forbid")

    account_holder_name: str = Field(min_length=1, max_length=100)
    account_type: AccountType
    status: AccountStatus
    balance: Money = Decimal("0.00")
    currency: Currency = "USD"
    date_opened: date | None = None
    owner_id: UserId


class BankAccount(BankAccountCreate):
    """An account as stored and returned by the API."""

    # Always set by the time an account is stored, so it is not optional here.
    account_number: AccountNumber
    date_opened: date

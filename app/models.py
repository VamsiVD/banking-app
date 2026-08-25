"""Pydantic models for the banking API.

`BankAccountCreate` is a direct translation of BankingApp.json — that file is the
contract, so keep the two in step. If you need a field the schema does not have,
change the schema in the same PR.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


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


# Money is Decimal, never float. 0.1 + 0.2 does not equal 0.3 in binary floating
# point, and a balance that drifts by a cent is a balance nobody can reconcile.
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]

AccountNumber = Annotated[str, Field(min_length=1, max_length=34)]
Currency = Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]


class BankAccountCreate(BaseModel):
    """Request body for creating an account."""

    # Mirrors "additionalProperties": false in BankingApp.json — an unexpected
    # key is a client bug, and silently dropping it hides the bug.
    model_config = ConfigDict(extra="forbid")

    account_number: AccountNumber
    account_holder_name: str = Field(min_length=1, max_length=100)
    account_type: AccountType
    status: AccountStatus
    balance: Money = Decimal("0.00")
    currency: Currency = "USD"
    date_opened: date | None = None


class BankAccount(BankAccountCreate):
    """An account as stored and returned by the API."""

    # Always set by the time an account is stored, so it is not optional here.
    date_opened: date


class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"


# Amounts on a movement are strictly positive; direction is carried by the type,
# never by a negative number. A "deposit of -50" should be impossible to express.
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]

class MoneyMovement(BaseModel):
    """Request body for a deposit or withdrawal."""

    model_config = ConfigDict(extra="forbid")

    amount: PositiveMoney
    description: str | None = Field(default=None, max_length=200)

class Transaction(BaseModel):
    """One immutable entry in the ledger.

    Written by the transactions router, read by the statements router. Nothing
    edits or deletes an entry — a correction is a new entry in the other
    direction. That is what makes the ledger auditable.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    account_number: AccountNumber
    type: TransactionType
    amount: PositiveMoney
    currency: Currency
    balance_after: Money
    # The other side of a transfer. None for deposits and withdrawals.
    counterparty: AccountNumber | None = None
    description: str | None = Field(default=None, max_length=200)
    timestamp: datetime

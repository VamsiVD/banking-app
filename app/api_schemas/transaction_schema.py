"""Transaction domain: movement type, request body, and ledger entry shape."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.api_schemas.primitives import AccountNumber, Currency, Money, PositiveMoney


class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"


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

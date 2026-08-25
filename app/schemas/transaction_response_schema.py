from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MoneyMovement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=200)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    account_number: str
    type: str
    amount: Decimal
    currency: str
    balance_after: Decimal
    counterparty: str | None = None
    description: str | None = Field(default=None, max_length=200)
    timestamp: datetime
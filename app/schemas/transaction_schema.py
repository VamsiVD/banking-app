from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MoneyMovement(BaseModel):
    """Request body for deposits and withdrawals."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=200)
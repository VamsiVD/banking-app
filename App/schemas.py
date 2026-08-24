from pydantic import BaseModel, Field
from typing import Literal
from datetime import date


class BankAccountCreate(BaseModel):
    account_number: str = Field(min_length=1, max_length=34)
    account_holder_name: str = Field(min_length=1, max_length=100)

    account_type: Literal[
        "checking",
        "savings",
        "business",
        "fixed_deposit"
    ]

    balance: float = Field(default=0, ge=0)

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3
    )

    date_opened: date | None = None

    status: Literal[
        "active",
        "inactive",
        "frozen",
        "closed"
    ]
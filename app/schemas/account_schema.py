from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.models import AccountStatus, AccountType


Money = Annotated[
    Decimal,
    Field(ge=0, max_digits=18, decimal_places=2)
]

AccountNumber = Annotated[
    str,
    Field(min_length=1, max_length=34)
]

Currency = Annotated[
    str,
    Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
]


class BankAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_number: AccountNumber
    account_holder_name: str = Field(min_length=1, max_length=100)
    account_type: AccountType
    status: AccountStatus
    balance: Money = Decimal("0.00")
    currency: Currency = "USD"
    date_opened: date | None = None


class BankAccountResponse(BaseModel):
    account_number: AccountNumber
    account_holder_name: str
    account_type: AccountType
    status: AccountStatus
    balance: Money
    currency: Currency
    date_opened: date
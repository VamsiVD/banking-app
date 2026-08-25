"""Request/response shapes for transfers.

Amounts appear in JSON as strings ("40.00"), not numbers. Pydantic serializes
Decimal that way on purpose: a JSON number is a float, which is exactly the
precision loss we are avoiding.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.models import AccountNumber, PositiveMoney, Transaction


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_account_number: AccountNumber
    to_account_number: AccountNumber
    amount: PositiveMoney
    description: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _reject_self_transfer(self) -> "TransferRequest":
        # A 422 rather than a domain error: this is a malformed request, knowable
        # from the body alone without consulting any account.
        if self.from_account_number == self.to_account_number:
            raise ValueError("from_account_number and to_account_number must differ.")
        return self


class TransferResult(BaseModel):
    """Both sides of a transfer. One movement, two ledger entries."""

    debit: Transaction
    credit: Transaction

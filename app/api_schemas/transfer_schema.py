"""Request/response shapes for transfers.

Amounts appear in JSON as strings ("40.00"), not numbers. Pydantic serializes
Decimal that way on purpose: a JSON number is a float, which is exactly the
precision loss we are avoiding.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api_schemas.primitives import AccountNumber, Currency, PositiveMoney
from app.api_schemas.transaction_schema import Transaction


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


class TransferSummary(BaseModel):
    """One transfer, as it reads back out of the ledger.

    Built from the `transfer_out` entry alone, which already records everything
    that identifies the transfer: who paid, who was paid, how much, why, when.

    The matching `transfer_in` entry is deliberately not included. Nothing links
    the two rows — no shared id, only a counterparty and timestamps a fraction of
    a millisecond apart — so pairing them means guessing, and a confidently wrong
    credit is worse than none. A `transfer_id` column would fix that properly.
    """

    # The debit entry's id. Stable, and what GET /transfers/{id} takes.
    id: str
    from_account_number: AccountNumber
    to_account_number: AccountNumber
    amount: PositiveMoney
    currency: Currency
    description: str | None = None
    timestamp: datetime


class TransferPage(BaseModel):
    """A page of transfers.

    An envelope rather than a bare array, because a bare array leaves nowhere to
    report `total` — and a client that cannot tell "20 results" from "20 of 400"
    cannot page. The queries and statements slices are asked to use this same
    shape; this is the first one to exist, so it sets it.
    """

    items: list[TransferSummary]
    # Matching transfers in total, not the length of `items`.
    total: int
    limit: int
    offset: int

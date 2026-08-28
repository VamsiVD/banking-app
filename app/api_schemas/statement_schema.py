"""Statement domain: a summary of one account's activity over a period."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.api_schemas.primitives import AccountNumber, Currency, Money


class AccountStatement(BaseModel):
    """Opening/closing balance and totals for one account, in one range.

    `period_start`/`period_end` are None when the caller asked for the whole
    history rather than a range — the statement still makes sense, it just
    covers everything on record.
    """

    model_config = ConfigDict(extra="forbid")

    account_number: AccountNumber
    currency: Currency
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Money
    closing_balance: Money
    total_in: Money
    total_out: Money
    entry_count: int

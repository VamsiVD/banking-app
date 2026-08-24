"""Money movement — deposits, withdrawals, transfers.

Owner: utoker
Branch: feat/transactions

Endpoints to build here:
    POST /accounts/{account_number}/deposit    add funds
    POST /accounts/{account_number}/withdraw   remove funds
    POST /transfers                            move funds between two accounts

Notes:
  - Amounts are Decimal and must be strictly positive. A zero or negative deposit
    is a validation error, not a no-op.
  - Only `active` accounts move money. Anything else is AccountNotActive (409).
  - Overdrawing is InsufficientFunds (409).
  - A transfer between different currencies is CurrencyMismatch (409) — this API
    does no FX conversion.
  - Wrap every read-modify-write in `with store.transaction():`. A transfer
    touches two accounts and must not interleave with another request.
"""

from fastapi import APIRouter

# No prefix: this router owns paths under both /accounts and /transfers.
router = APIRouter(tags=["transactions"])

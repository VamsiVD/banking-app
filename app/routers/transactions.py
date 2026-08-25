"""Money movement — deposits, withdrawals, transfers.

Owner: utoker
Branch: feat/transactions

Endpoints to build here:
    POST /accounts/{account_number}/deposit    add funds
    POST /accounts/{account_number}/withdraw   remove funds
    POST /transfers                            move funds between two accounts

Notes:
  - Amounts are Decimal and strictly positive (models.PositiveMoney). A zero or
    negative deposit is a validation error, not a no-op.
  - Only `active` accounts move money. Anything else is AccountNotActive (409).
  - Overdrawing is InsufficientFunds (409).
  - A transfer between different currencies is CurrencyMismatch (409) — this API
    does no FX conversion.
  - A transfer to and from the same account should be rejected, not silently
    succeed as a no-op.

  - Wrap every read-modify-write in `with store.transaction():`. A transfer
    touches two accounts and must not interleave with another request.
  - Write a ledger entry for every movement, inside that same block, so a balance
    and its history can never disagree:

        with store.transaction():
            account.balance += amount
            store.put(account)
            ledger.record(account.account_number, TransactionType.deposit,
                          amount, account.currency, account.balance)

    A transfer writes two entries — transfer_out on the source, transfer_in on
    the destination, each naming the other as `counterparty`.
"""

from fastapi import APIRouter

# No prefix: this router owns paths under both /accounts and /transfers.
router = APIRouter(tags=["transactions"])

"""Transaction history and statements.

Owner: D (unclaimed)
Branch: feat/statements

Endpoints to build here:
    GET /accounts/{account_number}/transactions   history for one account, with:
                                                    type          filter
                                                    from_date/to_date  date range
                                                    limit, offset paging
    GET /accounts/{account_number}/statement      summary over a period:
                                                    opening/closing balance,
                                                    totals in and out, entry count

Notes for whoever takes this:
  - Read through app/ledger.py. Never append here — writing is the transactions
    router's job, and the ledger is append-only besides.
  - Unknown account is AccountNotFound (404). An account with no movements yet is
    an empty list and a 200, not a 404 — those are different facts.
  - Newest-first is the more useful default for history; say so in the docstring
    either way, since the ledger hands you oldest-first.
  - Same paged envelope shape queries.py uses. Agree it with C so the two match.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/accounts", tags=["statements"])

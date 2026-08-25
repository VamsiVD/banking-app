"""Account lifecycle — create, fetch, change status.

Owner: A (unclaimed)
Branch: feat/accounts

Endpoints to build here:
    POST   /accounts                        create an account
    GET    /accounts/{account_number}       fetch one
    PATCH  /accounts/{account_number}/status  activate / freeze / close

Notes for whoever takes this:
  - The account_number is the key. There is no separate surrogate id.
  - Creating a number that already exists is a DuplicateAccount (409), not a 200.
  - `date_opened` is optional on input; default it to today when absent.
  - Raise from app.errors; do not raise HTTPException directly.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/accounts", tags=["accounts"])

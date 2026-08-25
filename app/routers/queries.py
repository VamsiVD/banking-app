"""Listing accounts — filtering, sorting, pagination.

Owner: C (unclaimed)
Branch: feat/queries

Endpoints to build here:
    GET /accounts   list accounts, with query parameters:
                      account_type, status, currency   filters
                      limit, offset                    pagination
                      sort_by, order                   sorting

Notes for whoever takes this:
  - Read through store.list_all(); filter and page in this file.
  - Return a paged envelope ({items, total, limit, offset}), not a bare array —
    a bare array leaves no room to report the total.
  - Cap `limit` so a client cannot ask for everything at once.
  - Sharing the /accounts prefix with accounts.py is fine; the methods differ.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/accounts", tags=["queries"])

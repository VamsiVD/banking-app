# Banking-app

A full-stack banking app: a FastAPI + PostgreSQL backend, and a React (Vite)
frontend ("Banks-R-Us" in the UI). Accounts, the transaction ledger, and
registered users/admins live in Postgres and survive a restart. Subscriptions
are the one exception — see
[Subscriptions: a service of its own](#subscriptions-a-service-of-its-own).

The design rule across the backend: **router (API) → service → core (rules +
store) → repository → schema.** A router only translates HTTP in and out; a
service holds the business logic; core rules are pure validation with no
I/O; repositories are thin wrappers over the store (or, for subscriptions, over
an HTTP client); schemas are the Pydantic shapes that cross every boundary.

**Where each slice stands:**
- **Auth** (customer and admin), **transfers**, **deposits/withdrawals**,
  **statements** and **subscriptions** are wired end to end (router → service
  → repository → store/client) and are the reference to copy.
- **Accounts** (`app/routers/accounts.py`) reads and writes `app.core.store`
  directly, so an account created there is immediately visible to transfers
  and to deposits/withdrawals. It does not go through
  `app/services/account_service.py`, which exists but is not yet wired to
  anything.
- **Listing/filtering** (`app/routers/queries.py`) is unclaimed — the router
  exists with a prefix and nothing else; see the docstring for the intended
  shape.

## Running it

You need Docker (for Postgres) and Node (for the frontend).

**Backend:**

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # once; .env is gitignored
# fill in DATABASE_URL, JWT_SECRET_KEY, and SUBSCRIPTION_TRACKER_BASE_URL
# (a reachable instance of the subscription-tracker service — local or the
# deployed one; see Subscriptions below)

docker compose up -d --wait      # starts Postgres, waits until it is ready

uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs, the interactive OpenAPI page.
`GET /health` should return `{"status": "ok"}`, and `GET /health/db` tells you
whether the database is actually reachable. Tables are created automatically
on startup from `app/sql_schemas/tables.py`.

**After every pull, restart the app.** Tables get created automatically, but
only new ones — if a table's columns changed, you get a confusing error rather
than a clear one, and someone needs to run the ALTER by hand.

**Frontend:**

```bash
cd webapp
npm install
npm run dev
```

Opens on http://localhost:5173. The dev server proxies `/api/*` (and, for now,
`/auth` and `/admin` directly — see `webapp/vite.config.js`) to the backend on
`:8000`, so the backend must already be running.

### Everyday Docker

```bash
docker compose ps                # status; you want "Up (healthy)"
docker compose logs -f db        # follow the logs
docker compose exec db psql -U banking -d banking    # a psql shell
docker compose down              # stop, keep the data
docker compose down -v           # stop and wipe the data volume
pytest                           # 125 tests; needs Postgres running
```

## Layout

| File | What lives there |
|---|---|
| `app/main.py` | App setup. Every router is registered here. |
| `app/config.py` | Settings from `.env` — `DATABASE_URL`, `JWT_SECRET_KEY`, `SUBSCRIPTION_TRACKER_BASE_URL`, and friends. |
| `app/db.py` | Engine, the per-request session, and the transaction primitive. |
| `app/errors.py` | Shared error types and the single error response shape. |
| `app/core/store.py` | The account + ledger store, backed by Postgres. Go through these functions, never raw SQL in a router. |
| `app/core/transfer_rules.py` | Pure transfer validation (active account, same currency, sufficient funds); no I/O. |
| `app/core/security.py` | Password hashing/verification, JWT issuing. |
| `app/core/auth_guard.py` | `get_current_user` / `get_current_admin` / `get_current_principal` — who is calling, and what they're allowed to be. |
| `app/sql_schemas/tables.py` | SQLAlchemy tables: the database's shape (accounts, transactions). |
| `app/sql_schemas/auth.py`, `app/sql_schemas/admin.py` | The `users` and `admins` tables. |
| `app/repositories/account_repository.py` | Account reads/writes, wrapping `core/store.py`. |
| `app/repositories/transaction_repository.py` | Ledger reads/writes, wrapping `core/store.py`. |
| `app/repositories/user_repository.py`, `app/repositories/admin_repository.py` | Registered users and admins. |
| `app/repositories/subscription_repository.py` | Subscription reads/writes. **Not** backed by this app's Postgres — proxies to the subscription-tracker service, translating field shapes both ways. |
| `app/clients/subscription_tracker_client.py` | Plain HTTP client for the subscription-tracker service. The only file that knows its base URL or wire shape. |
| `app/services/transfer_service.py` | Business logic for `/transfers`. |
| `app/services/transaction_service.py` | Business logic for deposit / withdraw. |
| `app/services/auth_service.py`, `app/services/admin_service.py` | Business logic for register/login, customer and admin. |
| `app/services/subscription_service.py` | Business logic for `/subscriptions`. |
| `app/services/account_service.py` | Account business logic. **Written but not wired to the router yet.** |
| `app/api_schemas/primitives.py` | Shared value types (`Money`, `PositiveMoney`, `AccountNumber`, `Currency`, `UserId`). |
| `app/api_schemas/*_schema.py` | Request/response shapes, one file per domain (accounts, auth, transactions, transfers, statements, subscriptions). |
| `app/routers/accounts.py` | Create / fetch / list / change status / delete accounts. |
| `app/routers/auth.py`, `app/routers/admin.py` | Register / login, customer and admin. |
| `app/routers/transactions.py` | Deposit / withdraw. |
| `app/routers/transfers.py` | Transfer funds between two accounts. Reference implementation for the layering. |
| `app/routers/statements.py` | Per-account statement: opening/closing balance, totals in/out, entry count. |
| `app/routers/subscriptions.py` | Create / list / fetch / delete subscriptions. Auth-gated; `owner_id` always comes from the token. |
| `app/routers/queries.py` | List, filter, page, sort accounts. **Unclaimed, still a stub.** |
| `webapp/src/api/client.js` | The one place the frontend talks to the API. Flattens both backend error shapes into one `ApiError`. |
| `webapp/src/App.jsx` | Sign-in / sign-up shell; routes to `LandingPage`, `CreateAccount`, `UserHome`, or `AdminHome` by session role. |
| `webapp/src/UserHome.jsx`, `webapp/src/AdminHome.jsx` | The customer and admin dashboards. |

## Conventions

These are the things that cut across everyone's work, so they are not up for
per-file interpretation:

- **`docs/BankingApp.json` is the contract.** Changing a field means changing
  the schema in the same PR.
- **Money is `Decimal`, never `float`.** Floats lose cents. Use the shared
  `Money`/`PositiveMoney` types from `app/api_schemas/primitives.py` instead
  of redeclaring the constraint. `balance` and `amount` are `NUMERIC(18,2)`
  and the database rejects anything else.
- **One error shape.** Raise the classes in `app/errors.py`; do not raise
  `HTTPException` directly and do not invent a new response body.
- **Reach the store through its functions**, and wrap any read-modify-write
  sequence in `with store.transaction():`.
- **Every movement of money writes a ledger entry**, in the same
  `store.transaction()` block that changes the balance. The ledger is
  append-only: corrections are new entries, never edits.
- **Keep the layering.** A router calls a service; a service calls
  repositories and core rules; a repository is the only thing that touches
  `core/store.py` (or, for subscriptions, the HTTP client). `accounts.py`
  still calls the store directly; fixing that is open work, not a reason to
  add more code that skips the layers.

## Working with the database

`store.get()` returns a `BankAccount`, `store.put()` writes one back, and
`store.transaction()` wraps a read-modify-write:

- **`transaction()` really rolls back.** If your handler raises halfway
  through, the whole block reverts.
- **`get()` inside a `transaction()` block locks the row** (`SELECT ... FOR
  UPDATE`) until the block ends. That is what stops two concurrent withdrawals
  from both passing the same balance check.

If you are about to write to **two** accounts, take them together with
`store.get_many_for_update([a, b])` rather than two `get()` calls. It sorts
before locking; locking in request order lets A→B and B→A deadlock, and
Postgres resolves that by killing one of them.

**Writing real queries.** `store.list_all()` returns every account. For
filtering, sorting and paging (the `queries.py` stub) do it in SQL:

```python
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.sql_schemas.tables import AccountRow

@router.get("/accounts")
def list_accounts(status: str | None = None, db: Session = Depends(get_session)):
    stmt = select(AccountRow).order_by(AccountRow.account_number).limit(50)
    if status:
        stmt = stmt.where(AccountRow.status == status)
    return [... for row in db.scalars(stmt)]
```

**Changing the schema.** Edit `app/sql_schemas/tables.py` (or `auth.py` /
`admin.py`). A brand-new table just appears next time the app (or `pytest`)
starts — `db.init_db()` calls `Base.metadata.create_all()`, which only
creates tables that do not exist yet.

**Altering an existing table** (new column, changed type, dropped constraint)
needs a manual `ALTER` run against the database yourself — `create_all()` will
not touch a table that already exists.

## Subscriptions: a service of its own

Every other slice keeps its rows in this app's Postgres. Subscriptions don't —
they live behind a separate, already-deployed API (its own Lambda, its own
Supabase Postgres, no relation to `DATABASE_URL`). `SUBSCRIPTION_TRACKER_BASE_URL`
in `.env` says where it is; `app/clients/subscription_tracker_client.py` is the
only file that talks to it.

**The login wall is still ours.** `/subscriptions` stays behind
`Depends(get_current_user)` like every other authenticated route. `owner_id`
comes from the caller's token, never from the request body or the URL — the
upstream service itself does not enforce that (see below), so this app is what
actually keeps one user from touching another's subscriptions.

**Field shapes don't match, on purpose.** The upstream service speaks its own
wire format (`uuid`, `type`, integer-cents `amount`, RFC3339 `start_date`).
This app keeps its own (`id`, `billing_cycle`, decimal `amount`, plain-date
`next_billing_date`) so the rest of the codebase — and the webapp — never had
to change. `app/repositories/subscription_repository.py` is where the two get
translated, both directions.

**The upstream service trusts the uuid alone.** Its `PATCH`/`DELETE` routes
take no owner check — anyone who knows a subscription's uuid could patch or
delete it directly against that service. `subscription_repository.py` closes
that gap on our side: before either operation it re-lists the caller's own
subscriptions and confirms the id is actually theirs, the same guarantee a
`WHERE owner_id = ...` clause used to give us for free.

**Failure there is a 502, not a 500.** If the service is unreachable or
answers with an error, that surfaces as
`{"error": {"code": "subscription_service_unavailable"}}` — a different code
from `internal_error`, because the failure is upstream, not a bug in this app.

## Working together

`main` is where work converges. Branch off it per feature/fix and PR back in.

- **Never force-push a branch other people are building on.** Corrections go
  on top as new commits.
- **Restart the app after every pull or merge**, not only after cloning. New
  tables pick themselves up; a changed column on an existing table needs the
  ALTER run by hand, or you get a confusing "column does not exist" instead.
- **Say so before changing a shared file** — `app/main.py`, `app/errors.py`,
  `app/db.py`, `app/sql_schemas/`, `app/config.py`, `app/core/store.py`, and
  anything in `app/api_schemas/` or `app/repositories/` — since other slices
  are built on top of them.

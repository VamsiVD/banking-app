# Banking-app

Training project: a banking backend API in Python + FastAPI, on PostgreSQL.

**Scope for this phase: API + database + auth.** No frontend. Accounts, the
transaction ledger and registered users live in Postgres and survive a restart.
Schema changes land in `app/tables.py` and are picked up automatically on the
next app start, so say so in the group before you change a table everyone
shares.

The design rule across the app: **router (API) → service → core (rules +
store) → repository → schema.** A router only translates HTTP in and out; a
service holds the business logic; core rules are pure validation with no
I/O; repositories are thin wrappers over the store; schemas are the Pydantic
shapes that cross every boundary.

**Where each slice stands:**
- **Transfers**, **deposits/withdrawals** and **auth** are wired end to end
  (router → service → repository → store) and are the reference to copy.
- **Accounts** (`app/routers/accounts.py`) reads and writes `app.core.store`,
  so an account created there is immediately visible to transfers and to
  deposits/withdrawals. It still calls the store directly rather than going
  through `app/services/account_service.py`, which exists but is not yet wired
  to anything.
- **Listing/filtering** (`queries.py`) and **statements** (`statements.py`)
  are unclaimed; see the docstring in each file for the intended shape.

## Running it

You need Docker. On WSL/Ubuntu, `bash scripts/install-docker-wsl.sh` installs
it; on macOS or plain Windows, install Docker Desktop.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # once; .env is gitignored
docker compose up -d --wait      # starts Postgres, waits until it is ready
python -m scripts.seed           # optional: five demo accounts

uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs, the interactive OpenAPI page is our
front end for this phase. `GET /health` should return `{"status": "ok"}`, and
`GET /health/db` tells you whether the database is actually reachable.
Tables are created automatically on startup from `app/tables.py`.

**After every pull, restart the app.** Tables get created automatically, but
only new ones — if a teammate changed an existing column you get a confusing
error rather than a clear one, and someone needs to run the ALTER by hand.

### Everyday Docker

```bash
docker compose ps                # status; you want "Up (healthy)"
docker compose logs -f db        # follow the logs
docker compose exec db psql -U banking -d banking    # a psql shell
docker compose down              # stop, keep the data
docker compose down -v           # stop and wipe the data volume
pytest                           # 72 tests; needs Postgres running
```

## Layout

| File | What lives there |
|---|---|
| `app/main.py` | App setup. Every router is already registered, so you should not need to edit this. |
| `app/config.py` | Settings from `.env`. `DATABASE_URL` lives here and nowhere else. |
| `app/db.py` | Engine, the per-request session, and the transaction primitive. |
| `app/tables.py` | SQLAlchemy tables: the database's shape. |
| `app/errors.py` | Shared error types and the single error response shape. |
| `app/core/store.py` | The account + ledger store, backed by Postgres. Go through these functions, never raw SQL in a router. |
| `app/core/transfer_rules.py` | Pure transfer validation (active account, same currency, sufficient funds); no I/O. |
| `app/core/security.py` | Password hashing/verification for auth. |
| `app/repositories/account_repository.py` | Account reads/writes, wrapping `core/store.py`. |
| `app/repositories/transaction_repository.py` | Ledger reads/writes, wrapping `core/store.py`. |
| `app/repositories/user_repository.py` | Registered-user records, in the `users` table. |
| `app/services/transfer_service.py` | Business logic for `/transfers`. |
| `app/services/transaction_service.py` | Business logic for deposit / withdraw. |
| `app/services/auth_service.py` | Business logic for register/login. |
| `app/services/account_service.py` | Account business logic. **Written but not wired to the router yet.** |
| `app/schemas/primitives.py` | Shared value types (`Money`, `AccountNumber`, `Currency`, `PositiveMoney`). |
| `app/schemas/account_schema.py` | Account request/response shapes. |
| `app/schemas/transaction_schema.py` | `MoneyMovement` request shape, ledger entry shape. |
| `app/schemas/transfer_schema.py` | Transfer request/response shapes. |
| `app/schemas/auth_schema.py` | Register/login request, user profile response. |
| `app/routers/accounts.py` | Create / fetch / list / change status / delete accounts. |
| `app/routers/auth.py` | Register / login. |
| `app/routers/transactions.py` | Deposit / withdraw. |
| `app/routers/transfers.py` | Transfer funds between two accounts. Reference implementation for the layering. |
| `app/routers/queries.py` | List, filter, page, sort accounts. **Unclaimed, still a stub.** |
| `app/routers/statements.py` | Transaction history and statements. **Unclaimed, still a stub.** |
| `scripts/seed.py` | The five demo accounts. Idempotent. |

## Conventions

These are the things that cut across everyone's work, so they are not up for
per-file interpretation:

- **`BankingApp.json` is the contract.** Changing a field means changing the
  schema in the same PR.
- **Money is `Decimal`, never `float`.** Floats lose cents. Use the shared
  `Money`/`PositiveMoney` types from `app/schemas/primitives.py` instead of
  redeclaring the constraint. `balance` and `amount` are `NUMERIC(18,2)` and
  the database rejects anything else.
- **One error shape.** Raise the classes in `app/errors.py`; do not raise
  `HTTPException` directly and do not invent a new response body.
- **Reach the store through its functions**, and wrap any read-modify-write
  sequence in `with store.transaction():`.
- **Every movement of money writes a ledger entry**, in the same
  `store.transaction()` block that changes the balance. The ledger is
  append-only: corrections are new entries, never edits.
- **Keep the layering.** A router calls a service; a service calls
  repositories and core rules; a repository is the only thing that touches
  `core/store.py`. `accounts.py` still calls the store directly; fixing that
  is open work, not a reason to add more code that skips the layers.

## Working with the database

Nothing about how you write a router changed when Postgres landed. `store.get()`
still returns a `BankAccount`, `store.put()` still writes one back, and
`store.transaction()` still wraps a read-modify-write. Two things are better:

- **`transaction()` really rolls back.** It used to be a mutex, which stopped
  two requests interleaving but could not undo a change once made. If your
  handler raises halfway through, the whole block reverts.
- **`get()` inside a `transaction()` block locks the row** (`SELECT ... FOR
  UPDATE`) until the block ends. That is what stops two concurrent withdrawals
  from both passing the same balance check.

If you are about to write to **two** accounts, take them together with
`store.get_many_for_update([a, b])` rather than two `get()` calls. It sorts
before locking; locking in request order lets A→B and B→A deadlock, and
Postgres resolves that by killing one of them.

**Writing real queries.** `store.list_all()` returns every account. For
filtering, sorting and paging (the queries and statements slices) do it in SQL:

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

**Changing the schema.** Edit `app/tables.py`. A brand-new table just appears
next time the app (or `pytest`) starts — `db.init_db()` calls
`Base.metadata.create_all()`, which only creates tables that do not exist yet.

**Altering an existing table** (new column, changed type, dropped constraint)
needs a manual `ALTER` run against the database yourself — `create_all()` will
not touch a table that already exists. Say so in the group chat so everyone
running against the shared table applies the same change, and note it in the
PR that changed `tables.py`.

## Working together

`feat/db-foundation` is the integration branch. Branch off it, one branch per
slice, and PR back into it when your slice is done:

```bash
git fetch upstream
git checkout -b feat/<slice> upstream/feat/db-foundation
```

**Do not branch off `api_endpoint_test`.** It predates the database — no
`app/db.py`, no `app/tables.py`, no `docker-compose.yml` — so a slice built on
it cannot be merged back without being rewritten.

Once people are branched off a shared moving branch, a few things start to
matter that did not before:

- **Never force-push `feat/db-foundation`.** Everyone is branched off it, and
  rewriting its history breaks all of them at once. Corrections go on top as
  new commits.
- **Merge it into your slice regularly**, not just at the end. A week of drift
  is a bad afternoon.
- **Restart the app after every pull or merge**, not only after cloning. New
  tables pick themselves up; a changed column on an existing table needs the
  ALTER run by hand, or you get a confusing "column does not exist" instead.

Each person owns one file under `app/routers/`. Shared files (`app/main.py`,
`app/errors.py`, `app/db.py`, `app/tables.py`, `app/config.py`,
`app/core/store.py`, the `app/schemas/` and `app/repositories/` modules) are
stable; if you need to change one, say so in the group first, because everyone
else is building on it.

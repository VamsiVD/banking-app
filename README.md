# Banking-app

Training project: a banking backend API in Python + FastAPI, on PostgreSQL.

**Scope for this phase — API + database + auth.** No frontend. Accounts, the
ledger and users live in Postgres and survive a restart. Schema changes go through
Alembic migrations, so tell the group before you change a table everyone shares.

## Running it

You need Docker. On WSL/Ubuntu, `bash scripts/install-docker-wsl.sh` installs it;
on macOS or plain Windows, install Docker Desktop.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # once; .env is gitignored
docker compose up -d --wait      # starts Postgres, waits until it is ready
alembic upgrade head             # creates the tables
python -m scripts.seed           # optional: the five demo accounts

uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs — the interactive OpenAPI page is our front
end for this phase. `GET /health` returns `{"status": "ok"}`, and `GET /health/db`
tells you whether the database is actually reachable.

**After every pull, run `alembic upgrade head`.** If a teammate added a table and
you skipped it, you get a confusing error about a missing column rather than a
clear one about a missing migration.

### Everyday Docker

```bash
docker compose up -d --wait      # start (blocks until Postgres accepts connections)
docker compose ps                # status — you want "Up (healthy)"
docker compose logs -f db        # follow the logs
docker compose exec db psql -U banking -d banking    # a psql shell
docker compose down              # stop, keep the data
docker compose down -v           # stop and wipe the data volume
pytest                           # 60 pass, 12 skipped; needs Postgres running
```

## Layout

| File | What lives there |
|---|---|
| `app/main.py` | App setup. Every router is registered here already. |
| `app/config.py` | Settings from `.env`. `DATABASE_URL` lives here and nowhere else. |
| `app/db.py` | Engine, per-request session, and the transaction primitive. |
| `app/tables.py` | SQLAlchemy tables — the database's shape. |
| `app/core/store.py` | Accounts and the ledger. Go through these functions, not raw SQL. |
| `app/core/transfer_rules.py` | Pure transfer policy — no I/O. |
| `app/core/security.py` | Password hashing. |
| `app/errors.py` | Shared error types and the single error response shape. |
| `app/schemas/` | Pydantic request/response models. `models.py` mirrors `BankingApp.json`. |
| `app/repositories/` | Data access for the services. |
| `app/services/` | Business logic — transfers, auth. |
| `app/routers/` | HTTP controllers, one slice per file. |
| `alembic/versions/` | Migrations. One file per schema change, committed with the change. |
| `scripts/seed.py` | The five demo accounts. Idempotent. |

## Conventions

- **`BankingApp.json` is the contract.** Changing a field means changing the
  schema in the same PR. Same for `AuthSchema.json`.
- **Money is `Decimal`, never `float`.** Floats lose cents. `balance` and `amount`
  are `NUMERIC(18,2)` and the database rejects anything else.
- **One error shape.** Raise the classes in `app/errors.py`; do not raise
  `HTTPException` directly and do not invent a new response body.
- **Reach the store through its functions**, and wrap any read-modify-write
  sequence in `with store.transaction():`.
- **Every movement of money writes a ledger entry**, in the same
  `store.transaction()` block that changes the balance. The ledger is
  append-only: corrections are new entries, never edits.

## Working with the database

Nothing about how you write a router changed when Postgres landed. `store.get()`
still returns a `BankAccount`, `store.put()` still writes one back, and
`store.transaction()` still wraps a read-modify-write. Two things are better:

- **`transaction()` really rolls back.** It used to be a mutex, which stopped two
  requests interleaving but could not undo a change once made. If your handler
  raises halfway through, the whole block reverts.
- **`get()` inside a `transaction()` block locks the row** (`SELECT ... FOR
  UPDATE`) until the block ends. That is what stops two concurrent withdrawals
  from both passing the same balance check.

If you are about to write to **two** accounts, take them together with
`store.get_many_for_update([a, b])` rather than two `get()` calls. It sorts before
locking; locking in request order lets A→B and B→A deadlock, and Postgres resolves
that by killing one of them.

**Writing real queries.** `store.list_all()` returns every account. For filtering,
sorting and paging — the queries and statements slices — do it in SQL instead:

```python
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.tables import AccountRow

@router.get("/accounts")
def list_accounts(status: str | None = None, db: Session = Depends(get_session)):
    stmt = select(AccountRow).order_by(AccountRow.account_number).limit(50)
    if status:
        stmt = stmt.where(AccountRow.status == status)
    return [... for row in db.scalars(stmt)]
```

**Changing the schema.** Edit `app/tables.py`, then:

```bash
alembic revision --autogenerate -m "add statements view"   # writes the migration
alembic upgrade head                                       # applies it
```

Read the generated file before committing — autogenerate is good at columns and
bad at intent. One trap: name a CHECK constraint **without** the `ck_<table>_`
prefix, because the naming convention in `tables.py` adds it; spelling the full
name gets it applied twice and autogenerate then reports a diff forever.

Commit the migration in the same PR as the table change, and say so in the group
chat so everyone knows to upgrade.

## Working together

Branch off `api_endpoint_test`, one branch per slice:

```bash
git fetch upstream
git checkout -b feat/<slice> upstream/api_endpoint_test
```

Each person owns one file under `app/routers/`. Shared files (`main.py`,
`errors.py`, `db.py`, `tables.py`, `config.py`, `core/store.py`) are stable — if
you need to change one, say so in the group first, because everyone else is
building on it.

## Known gap: deposit and withdraw

`POST /accounts/{n}/deposit` and `/withdraw` in `app/routers/transactions.py`
currently echo the request body back. They do not change a balance and they do not
write a ledger entry, so money only moves through `POST /transfers` today.

Everything they need is in place — `store.transaction()`, `store.get()` under a
row lock, `store.put()`, `store.record()`. The transfers slice is the worked
example, and `tests/test_transactions.py` already describes the intended
behaviour: twelve cases are skipped behind one marker at the top of that file.
Wire the endpoints to the store, delete the marker, and they should pass.

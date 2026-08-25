# Banking-app

Training project: a banking backend API in Python + FastAPI.

**Scope for this phase: API only, in-memory storage.** No real database yet.
Accounts, the transaction ledger, and registered users all live in
process-memory structures under `app/core/` and `app/repositories/`, and
reset whenever the server restarts. That is deliberate; do not add
persistence without agreeing it with the team first.

The design rule across the app: **router (API) → service → core (rules +
store) → repository → schema.** A router only translates HTTP in and out; a
service holds the business logic; core rules are pure validation with no
I/O; repositories are thin wrappers over the store; schemas are the Pydantic
shapes that cross every boundary.

**Not every slice follows that rule yet:**
- **Transfers** and **auth** are wired end to end (router → service → core
  → repository) and are the reference to copy.
- **Accounts** (`app/routers/accounts.py`) still keeps its own private list
  of dicts instead of going through `app.core.store`. That means an account
  created here is invisible to transfers and deposits/withdrawals, which
  both read `store`: a known bug, not a design choice.
- **Deposit/withdraw** (`app/routers/transactions.py`) are still stubs: they
  validate the request body and echo it back, with no service, no balance
  change, and no ledger entry written.
- **Listing/filtering** (`queries.py`) and **statements** (`statements.py`)
  are unclaimed; see the docstring in each file for the intended shape.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Auth needs `AUTH_SECRET_KEY` set in `.env`; `app/main.py` loads it with
`python-dotenv`.

Then open http://127.0.0.1:8000/docs, the interactive OpenAPI page is our
front end for this phase. `GET /health` should return `{"status": "ok"}`.

## Layout

| File | What lives there |
|---|---|
| `app/main.py` | App setup. Every router is already registered, so you should not need to edit this. |
| `app/errors.py` | Shared error types and the single error response shape. |
| `app/core/store.py` | The in-memory account + ledger store. Go through these functions, never the underlying dict. |
| `app/core/transfer_rules.py` | Pure transfer validation (active account, same currency, sufficient funds); no I/O. |
| `app/core/security.py` | Password hashing/verification for auth. |
| `app/repositories/account_repository.py` | Account reads/writes, wrapping `core/store.py`. Used by the transfer slice. |
| `app/repositories/user_repository.py` | Registered-user records, in-memory. |
| `app/services/transfer_service.py` | Business logic for `/transfers`. |
| `app/services/auth_service.py` | Business logic for register/login. |
| `app/schemas/primitives.py` | Shared value types (`Money`, `AccountNumber`, `Currency`, `PositiveMoney`). |
| `app/schemas/account_schema.py` | Account request/response shapes. |
| `app/schemas/transaction_schema.py` | `MoneyMovement` request shape, ledger entry shape. |
| `app/schemas/transfer_schema.py` | Transfer request/response shapes. |
| `app/schemas/auth_schema.py` | Register/login request, user profile response. |
| `app/routers/accounts.py` | Create / fetch / list / change status / delete accounts. **Bug: uses its own private list, not `store`; see above.** |
| `app/routers/auth.py` | Register / login. |
| `app/routers/transactions.py` | Deposit / withdraw. **Stub, not wired to a service yet.** |
| `app/routers/transfers.py` | Transfer funds between two accounts. Reference implementation for the layering. |
| `app/routers/queries.py` | List, filter, page, sort accounts. **Unclaimed, still a stub.** |
| `app/routers/statements.py` | Transaction history and statements. **Unclaimed, still a stub.** |

## Conventions

These are the things that cut across everyone's work, so they are not up for
per-file interpretation:

- **`BankingApp.json` is the contract.** Changing a field means changing the
  schema in the same PR.
- **Money is `Decimal`, never `float`.** Floats lose cents. Use the shared
  `Money`/`PositiveMoney` types from `app/schemas/primitives.py` instead of
  redeclaring the constraint.
- **One error shape.** Raise the classes in `app/errors.py`; do not raise
  `HTTPException` directly and do not invent a new response body.
- **Reach the store through its functions**, and wrap any read-modify-write
  sequence in `with store.transaction():`.
- **Every movement of money writes a ledger entry**, in the same
  `store.transaction()` block that changes the balance. The ledger is
  append-only: corrections are new entries, never edits.
- **Keep the layering.** A router calls a service; a service calls
  repositories and core rules; a repository is the only thing that touches
  `core/store.py`. `accounts.py` and `transactions.py` do not follow this
  yet; fixing that is open work, not a reason to add more code that skips
  the layers.

## Working together

Branch off `main`, one branch per slice, PR back into `VamsiVD/banking-app`:

```bash
git fetch upstream
git checkout -b feat/<slice> upstream/main
```

Each person owns one file under `app/routers/`. Shared files (`app/main.py`,
`app/errors.py`, `app/core/store.py`, the `app/schemas/` and
`app/repositories/` modules) are stable after the skeleton lands; if you
need to change one, say so in the group first, because everyone else is
building on it.

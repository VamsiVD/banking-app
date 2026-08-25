# Banking-app

Training project: a banking backend API in Python + FastAPI.

**Scope for this phase — API only.** No database, no frontend, no auth. Accounts
live in a module-level dict that resets whenever the server restarts. That is
deliberate; do not add persistence without agreeing it with the team first.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs — the interactive OpenAPI page is our
front end for this phase. `GET /health` should return `{"status": "ok"}`.

## Layout

| File | What lives there |
|---|---|
| `app/main.py` | App setup. Every router is already registered — you should not need to edit this. |
| `app/models.py` | Pydantic models. `BankAccountCreate` mirrors `BankingApp.json`. |
| `app/store.py` | The in-memory account store. Go through these functions, never the dict. |
| `app/ledger.py` | The in-memory transaction ledger. Append-only. |
| `app/errors.py` | Shared error types and the single error response shape. |
| `app/routers/accounts.py` | Create / fetch / change status — owner A |
| `app/routers/transactions.py` | Deposit / withdraw / transfer — owner utoker |
| `app/routers/queries.py` | List, filter, page, sort — owner C |
| `app/routers/statements.py` | Transaction history and statements — owner D |

## Conventions

These are the things that cut across everyone's work, so they are not up for
per-file interpretation:

- **`BankingApp.json` is the contract.** Changing a field means changing the
  schema in the same PR.
- **Money is `Decimal`, never `float`.** Floats lose cents.
- **One error shape.** Raise the classes in `app/errors.py`; do not raise
  `HTTPException` directly and do not invent a new response body.
- **Reach the store through its functions**, and wrap any read-modify-write
  sequence in `with store.transaction():`.
- **Every movement of money writes a ledger entry**, in the same
  `store.transaction()` block that changes the balance. The ledger is
  append-only: corrections are new entries, never edits.

## Working together

Branch off `main`, one branch per slice, PR back into `VamsiVD/banking-app`:

```bash
git fetch upstream
git checkout -b feat/<slice> upstream/main
```

Each person owns one file under `app/routers/`. Shared files (`main.py`,
`models.py`, `store.py`, `ledger.py`, `errors.py`) are stable after the skeleton lands — if
you need to change one, say so in the group first, because everyone else is
building on it.

# Demo: the transfers slice

Keep this open on a second screen. Every number below was checked against a
freshly seeded database — if one does not match on the day, something changed
and it is worth finding out what before carrying on.

## Before you share your screen

```bash
docker compose up -d --wait      # "Up (healthy)" before you go any further
alembic upgrade head
python -m scripts.seed --reset   # puts the five demo accounts back to their starting balances
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and collapse every section. Have a second
terminal ready for the restart in step 6.

Starting balances after `--reset`:

| account | holder | balance | status |
|---|---|---|---|
| 1001 | Sana Smith | 1500.00 | active |
| 1002 | Alex Walker | 800.00 | active |
| 1003 | Ria Sen | 5200.00 | active |
| 1004 | Dylan Sharma | 10000.00 | inactive |
| 1005 | Rinal Das | 250.00 | frozen |

Rerun `python -m scripts.seed --reset` between rehearsals.

---

## 1. The database is really there

**`GET /health/db`** → `{"status":"ok","database":"ok"}`

Worth thirty seconds: `/health` answers "did the process start", which stays
true while Postgres is down. `/health/db` answers "can I serve a request".
Two different questions, two endpoints.

## 2. Accounts come out of Postgres

**`GET /accounts/`** → the five accounts.

Point at the balance: **`"1500.00"` — a string, not `1500.0`.** That is
`NUMERIC(18,2)` arriving as a `Decimal` and being serialised as text. A JSON
number is a float, and floats lose cents.

## 3. Make a transfer

**`POST /transfers`**

```json
{
  "from_account_number": "1001",
  "to_account_number": "1002",
  "amount": "250.00",
  "description": "demo transfer"
}
```

**201**, and the response has *both* sides:

- `debit`  — account 1001, `transfer_out`, `balance_after: "1250.00"`, counterparty 1002
- `credit` — account 1002, `transfer_in`,  `balance_after: "1050.00"`, counterparty 1001

One movement, two ledger entries, written in a single database transaction. If
anything had failed between them, neither would exist.

## 4. Read the transfer back

**`GET /transfers`** → `{"items": [...], "total": 1, "limit": 50, "offset": 0}`

This is the transfer as an *event*, not just its effect on two balances. Copy
the `id` out of `items[0]`.

**`GET /transfers/{id}`** → the same transfer on its own.

If asked why there is a `total` next to the items: so a client can tell "20
results" from "20 of 400". A bare array cannot say that.

## 5. One dataset, not two

**`GET /accounts/1001`** → `"1250.00"`  ·  **`GET /accounts/1002`** → `"1050.00"`

The accounts endpoints and the transfer endpoints agree, because they read the
same rows. They did not always: `/accounts` used to serve a hardcoded list while
the money endpoints used the store, so the same account had two different
balances depending on which endpoint you asked.

## 6. The part that matters — restart it

Stop `uvicorn` with Ctrl-C in the other terminal. Start it again. Then:

**`GET /accounts/1001`** → still **`1250.00`**
**`GET /transfers`** → still `total: 1`

Nothing was kept in memory. That is the whole assignment in one click.

## 7. Refusals, all one shape

| Try | Result |
|---|---|
| `POST /transfers` 1002 → 1001, `"999999.00"` | **409** `insufficient_funds` |
| `POST /transfers` **1005** → 1001, `"1.00"` | **409** `account_not_active` (1005 is frozen) |
| `POST /transfers` 1001 → **1001**, `"1.00"` | **422** `validation_error` |

Every one comes back as `{"error": {"code": ..., "message": ...}}`. A client
branches on `code`; it never parses prose.

The self-transfer is a 422 rather than a 409 on purpose — it is knowable from
the request body alone, without consulting a single account.

---

## If someone asks a harder question

**"What if two transfers happen at once?"** `store.get()` inside a
`transaction()` block takes `SELECT ... FOR UPDATE`, so the second waits for the
first. `tests/test_transfers.py::test_concurrent_transfers_cannot_overdraw`
fires 150 threads at a balance of 100.00 and asserts exactly 100 succeed.

**"What about A→B and B→A at the same time?"** That deadlocks if you lock rows in
the order the request names them — Postgres kills one and a valid transfer 500s.
`store.get_many_for_update()` sorts the account numbers first, so everyone locks
in the same order. Reproduced before the fix went in;
`tests/test_db_foundation.py::test_opposite_transfers_do_not_deadlock` holds it.

**"Can I see both sides of a transfer from its id?"** Not today. The two ledger
entries share no id — only a counterparty and timestamps a fraction of a
millisecond apart — so pairing them would be guesswork. `GET /transfers` reads
the debit row, which already names both accounts. A `transfer_id` column is the
proper fix and is worth proposing to the team.

**"Why can't the balance go negative?"** Two reasons, deliberately. The service
refuses it, and `accounts.balance` carries a `CHECK (balance >= 0)`, so it holds
even against a stray `UPDATE` from a psql prompt.

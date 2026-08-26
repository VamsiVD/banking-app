# Demo: the transfers slice on PostgreSQL

Three things to show: **the database is really connected**, **the tests pass**, and
**transfers work against it**. About eight minutes.

Every number below was checked against a freshly seeded database. If one does not match
on the day, something changed — worth finding out what before carrying on.

---

## Before you share your screen

```bash
source .venv/bin/activate        # FIRST, in every terminal you use
docker compose up -d --wait      # must reach "healthy" before anything else matters
alembic upgrade head
python -m scripts.seed --reset   # puts the five demo accounts back to their starting balances
uvicorn app.main:app --reload
```

**Activate the venv in every terminal, including the second one.** `pytest`, `alembic`
and `uvicorn` all live in `.venv/bin/` and are not on the system PATH — without it the
first thing you type gets `command not found` in front of an audience. Check with
`which pytest`: it should print a path inside the project, not nothing.

Open http://127.0.0.1:8000/docs and collapse every section. Have a **second terminal**
ready — you need it for the tests and for the restart in Part 3. Activate the venv there
too.

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

# Part 1 — the database is really there (~2 min)

**The container is up and healthy:**

```bash
docker compose ps
```

`Up (healthy)` — not just "Up". The healthcheck means Postgres is accepting
connections, which is a different claim from "the process started".

**The app can reach it:**

`GET /health/db` → `{"status":"ok","database":"ok"}`

Worth thirty seconds on why this is separate from `/health`: `/health` answers "did the
process start", and stays green while Postgres is down. `/health/db` answers "can I
actually serve a request".

**The data is in Postgres, not in Python** — this is the strongest thing you can show:

```bash
docker compose exec db psql -U banking -d banking \
  -c "SELECT account_number, account_holder_name, balance, status FROM accounts ORDER BY 1;"
```

```
 account_number | account_holder_name | balance  |  status
----------------+---------------------+----------+----------
 1001           | Sana Smith          |  1500.00 | active
 1002           | Alex Walker         |   800.00 | active
 ...
```

Then `\d transactions` if anyone wants to see the schema: `NUMERIC(18,2)` for money,
a foreign key to `accounts`, and a `CHECK (amount > 0)`.

---

# Part 2 — the tests (~2 min)

**The headline:**

```bash
source .venv/bin/activate     # if this is a fresh terminal
pytest -q                     # 87 passed
```

**Then the transfers slice, verbosely** — this is the better screenshare, because the
names read as a specification rather than a row of dots:

```bash
pytest tests/test_transfers.py -v      # 31 passed
```

```
test_transfer_moves_money_between_accounts PASSED
test_transfer_conserves_the_total PASSED
test_overdraft_is_refused_and_changes_nothing PASSED
test_transfer_across_currencies_is_refused PASSED
test_transfer_from_a_frozen_account_is_refused PASSED
test_transfer_to_self_is_refused PASSED
...
```

Two worth pointing at by name:

- **`test_transfer_conserves_the_total`** — money is never created or destroyed by a
  transfer, only moved.
- **`test_concurrent_transfers_cannot_overdraw`** — 150 threads race to move 1.00 out of
  a balance of 100.00. Exactly 100 succeed. That is `SELECT ... FOR UPDATE` doing its
  job; without the row lock, two threads read the same balance and both pass the check.

These run against the real `banking_test` database, not a mock. The suite creates its
schema by running the actual migrations, so a broken migration fails the tests too.

---

# Part 3 — transfers against the live database (~4 min)

## Money is Decimal, never float

`GET /accounts/` → point at the balance: **`"1500.00"` is a string, not `1500.0`.**

`NUMERIC(18,2)` arrives as a Python `Decimal` and is serialised as text on purpose. A
JSON number is a float, and floats lose cents.

## Make a transfer

`POST /transfers`

```json
{
  "from_account_number": "1001",
  "to_account_number": "1002",
  "amount": "250.00",
  "description": "demo transfer"
}
```

**201**, and the response carries *both* sides:

- `debit`  — 1001, `transfer_out`, `balance_after: "1250.00"`, counterparty 1002
- `credit` — 1002, `transfer_in`,  `balance_after: "1050.00"`, counterparty 1001

One movement, two ledger entries, one database transaction. Had anything failed between
them, neither would exist.

## Read it back

`GET /transfers` → `{"items": [...], "total": 1, "limit": 50, "offset": 0}`

The transfer as an *event*, not just its effect on two balances. Copy the `id` from
`items[0]`, then `GET /transfers/{id}`.

If anyone asks about `total`: it lets a client tell "20 results" from "20 of 400". A
bare array cannot say that.

## One dataset

`GET /accounts/1001` → `"1250.00"`  ·  `GET /accounts/1002` → `"1050.00"`

The accounts endpoints and the transfer endpoints agree because they read the same rows.
They did not always: `/accounts` used to serve a hardcoded list while the money
endpoints used the store, so one account had two different balances depending on which
endpoint you asked.

## The closing beat — restart the server

Ctrl-C `uvicorn` in the second terminal. Start it again. Then:

- `GET /accounts/1001` → still **1250.00**
- `GET /transfers` → still `total: 1`

Nothing lived in memory. That is the assignment in one click.

## Refusals, all one shape

| Try | Result |
|---|---|
| `POST /transfers` 1002 → 1001, `"999999.00"` | **409** `insufficient_funds` |
| `POST /transfers` **1005** → 1001, `"1.00"` | **409** `account_not_active` (1005 is frozen) |
| `POST /transfers` 1001 → **1001**, `"1.00"` | **422** `validation_error` |

Every one is `{"error": {"code": ..., "message": ...}}`. A client branches on `code`; it
never parses prose.

The self-transfer is a 422 rather than a 409 deliberately — it is knowable from the
request body alone, without consulting a single account.

---

## If something goes wrong

| Symptom | Fix |
|---|---|
| `pytest: command not found` (or `alembic`, `uvicorn`) | `source .venv/bin/activate` — this terminal has no venv |
| Balances are not the starting numbers | `python -m scripts.seed --reset` |
| `Cannot reach PostgreSQL` on startup | `docker compose up -d --wait` |
| `relation "accounts" does not exist` | `alembic upgrade head` |
| `permission denied ... docker.sock` | `newgrp docker` |
| Anything else odd | `docker compose ps` first — if it is not `healthy`, nothing else will work |

## If someone asks a harder question

**"What if two transfers happen at once?"** `store.get()` inside a `transaction()` block
takes `SELECT ... FOR UPDATE`, so the second waits. That is what
`test_concurrent_transfers_cannot_overdraw` proves.

**"What about A→B and B→A simultaneously?"** That deadlocks if you lock rows in the
order the request names them — Postgres kills one and a valid transfer 500s.
`store.get_many_for_update()` sorts the account numbers first, so every caller locks in
the same order. It was reproduced before the fix went in;
`tests/test_db_foundation.py::test_opposite_transfers_do_not_deadlock` holds it.

**"Can I see both sides of a transfer from its id?"** Not today. The two ledger entries
share no id — only a counterparty and timestamps a fraction of a millisecond apart — so
pairing them would be guesswork. `GET /transfers` reads the debit row, which already
names both accounts. A `transfer_id` column is the proper fix, and is a change worth
proposing to the team.

**"Why can't a balance go negative?"** Two reasons, deliberately. The service refuses
it, *and* `accounts.balance` carries `CHECK (balance >= 0)` — so it holds even against a
stray `UPDATE` typed at a psql prompt.

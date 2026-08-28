"""Put the five demo accounts into the database.

    python -m scripts.seed

These used to live in a list inside `app/routers/accounts.py`, copied into the
store at import time by a `load_accounts()` call. That cannot work against a real
database: it ran on every import, before migrations had necessarily been applied,
and wrote to a table the rest of the app was already using. Seeding is a thing you
do once, on purpose, so it is a command.

Idempotent — an account that already exists is left exactly as it is, balance
included. Run it as often as you like; it will not undo your testing.

    python -m scripts.seed --reset

wipes accounts, the ledger and users first, then seeds. That is for rehearsing a
demo, where the point is to start from the same numbers every time.
"""

import argparse
import sys
from datetime import date
from decimal import Decimal

from app import db
from app.core import security
from app.config import get_settings
from app.core import store
from app.repositories.user_repository import user_repository
from app.api_schemas.account_schema import BankAccount

DEMO_ACCOUNTS = [
    ("1001", "Sana Smith", "savings", "1500.00", "2026-08-25", "active"),
    ("1002", "Alex Walker", "checking", "800.00", "2026-08-25", "active"),
    ("1003", "Ria Sen", "business", "5200.00", "2026-08-20", "active"),
    ("1004", "Dylan Sharma", "fixed_deposit", "10000.00", "2026-08-18", "inactive"),
    ("1005", "Rinal Das", "checking", "250.00", "2026-08-15", "frozen"),
]


def _demo_owner_id(holder: str) -> str:
    """Each demo account gets its own demo user, derived from the holder name."""
    return holder.lower().replace(" ", ".") + "@demo.bank"


def _ensure_demo_owner(holder: str) -> str:
    owner_id = _demo_owner_id(holder)
    if user_repository.get_by_email(owner_id) is None:
        user_repository.create(owner_id, holder, security.hash_password("changeme123"))
    return owner_id


def seed() -> tuple[int, int]:
    """Insert any missing demo accounts (and their owning demo users). Returns (created, skipped)."""
    created = skipped = 0

    for number, holder, kind, balance, opened, status in DEMO_ACCOUNTS:
        owner_id = _ensure_demo_owner(holder)

        if store.exists(number):
            print(f"  = {number}  {holder:14} already present, left alone")
            skipped += 1
            continue

        store.add(
            BankAccount(
                account_number=number,
                account_holder_name=holder,
                account_type=kind,
                status=status,
                # Decimal from a string, never float. Decimal(1500.0) would carry
                # the float's rounding error straight into the balance.
                balance=Decimal(balance),
                currency="USD",
                date_opened=date.fromisoformat(opened),
                owner_id=owner_id,
            )
        )
        print(f"  + {number}  {holder:14} {balance:>10} USD  {status}")
        created += 1

    return created, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe accounts, transactions and users first. For rehearsing a demo.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.reset and settings.TEST_DATABASE_URL == settings.DATABASE_URL:
        # The suite truncates between cases, so these are meant to differ. If they
        # do not, someone's .env is wrong and --reset is about to prove it loudly.
        sys.exit(
            "Refusing to reset: DATABASE_URL and TEST_DATABASE_URL are the same "
            "database. Fix .env before running this."
        )

    db.init_db()

    # Outside a request there is no middleware to open a session, so open one.
    with db.session_scope():
        if args.reset:
            # Say what is about to go, because there is no undo.
            existing = len(store.list_all())
            print(f"Resetting: dropping {existing} account(s), the whole ledger, "
                  f"and every registered user.")
            store.reset()
        created, skipped = seed()

    print(f"\nSeeded {created} account(s), left {skipped} untouched.")
    if created:
        print("Check it: curl http://127.0.0.1:8000/accounts/")


if __name__ == "__main__":
    main()

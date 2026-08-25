"""Initial schema: accounts and transactions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-25

Deliberately self-contained: no imports from `app`. A migration is a snapshot of
what the schema looked like at one moment, and it has to keep replaying correctly
years later. Importing app.models would mean that renaming an enum member today
silently rewrites history and breaks a fresh `upgrade head`.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# Column widths are the longest member of each set; the CHECK is what actually
# constrains the value.
ACCOUNT_TYPES = ("checking", "savings", "business", "fixed_deposit")
ACCOUNT_STATUSES = ("active", "inactive", "frozen", "closed")
TRANSACTION_TYPES = ("deposit", "withdrawal", "transfer_in", "transfer_out")


# CHECK constraint names are given WITHOUT the "ck_<table>_" prefix: the naming
# convention in tables.py adds it. Spelling the full name here gets it applied
# twice ("ck_accounts_ck_accounts_..."), and autogenerate then reports a diff
# on every run forever.
def _in_list(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_number", sa.String(length=34), nullable=False),
        sa.Column("account_holder_name", sa.String(length=100), nullable=False),
        sa.Column("account_type", sa.String(length=13), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        # NUMERIC, never FLOAT: a balance that drifts by a cent is a balance
        # nobody can reconcile.
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("date_opened", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("account_number", name="pk_accounts"),
        sa.CheckConstraint("balance >= 0", name="balance_non_negative"),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name="currency_is_iso_4217"
        ),
        sa.CheckConstraint(
            _in_list("account_type", ACCOUNT_TYPES), name="account_type"
        ),
        sa.CheckConstraint(
            _in_list("status", ACCOUNT_STATUSES), name="account_status"
        ),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("account_number", sa.String(length=34), nullable=False),
        sa.Column("type", sa.String(length=12), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("counterparty", sa.String(length=34), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.ForeignKeyConstraint(
            ["account_number"],
            ["accounts.account_number"],
            name="fk_transactions_account_number_accounts",
        ),
        # Direction is carried by `type`; the amount is always positive.
        sa.CheckConstraint("amount > 0", name="amount_positive"),
        sa.CheckConstraint(
            _in_list("type", TRANSACTION_TYPES), name="transaction_type"
        ),
    )
    # The statements router pages one account's history in time order.
    op.create_index(
        "ix_transactions_account_number_timestamp",
        "transactions",
        ["account_number", "timestamp"],
    )

    op.create_table(
        "users",
        # The email doubles as the id, matching what UserRepository already did.
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        # bcrypt output is bytes; BYTEA stores it without an encode/decode round trip.
        sa.Column("hashed_password", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        # Two simultaneous registrations can both pass a Python-level check;
        # this is what actually decides.
        sa.UniqueConstraint("email", name="uq_users_email"),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_index(
        "ix_transactions_account_number_timestamp", table_name="transactions"
    )
    op.drop_table("transactions")
    op.drop_table("accounts")

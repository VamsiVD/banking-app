"""Link accounts to users: accounts.owner_id -> users.id.

Revision ID: 0002_link_accounts_to_users
Revises: 0001_initial
Create Date: 2026-08-26

Deliberately self-contained: no imports from `app`, same reasoning as
0001_initial — a migration is a snapshot of one moment in the schema and has
to keep replaying correctly years later.

Added in three steps rather than one, because accounts already exist by the
time this runs. `ADD COLUMN ... NOT NULL` with nothing to put in the existing
rows fails outright:

    column "owner_id" of relation "accounts" contains null values

The test database is empty when the suite migrates it, so `pytest` never sees
that — only a development database with data does. Hence: add the column
nullable, give the existing rows an owner, then tighten it.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_link_accounts_to_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

# Accounts that predate ownership are parked on this user. A real address would
# imply somebody can log in as it; this one cannot, and it is obvious in psql
# which rows were backfilled rather than created with an owner.
LEGACY_OWNER_ID = "system@migration.local"


def upgrade() -> None:
    # 1. Nullable first, so the rows that already exist are allowed through.
    op.add_column(
        "accounts",
        sa.Column("owner_id", sa.String(length=255), nullable=True),
    )

    # 2. Give them an owner. The users table may be empty, so the placeholder
    #    has to be created before anything can point at it. ON CONFLICT keeps
    #    this replayable and harmless on a database that already has it.
    #    The password hash is deliberately not a valid bcrypt hash: bcrypt
    #    rejects it, so no login can ever succeed as this user.
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, full_name, hashed_password, created_at)
            VALUES (
                :owner_id, :owner_id, 'Migrated Accounts',
                '\\x6e6f742d612d68617368'::bytea, NOW()
            )
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(owner_id=LEGACY_OWNER_ID)
    )
    op.execute(
        sa.text(
            "UPDATE accounts SET owner_id = :owner_id WHERE owner_id IS NULL"
        ).bindparams(owner_id=LEGACY_OWNER_ID)
    )

    # 3. Now every row has a value, so the constraint can go on.
    op.alter_column("accounts", "owner_id", existing_type=sa.String(length=255), nullable=False)

    op.create_foreign_key(
        "fk_accounts_owner_id_users",
        "accounts",
        "users",
        ["owner_id"],
        ["id"],
    )
    op.create_index("ix_accounts_owner_id", "accounts", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_accounts_owner_id", table_name="accounts")
    op.drop_constraint(
        "fk_accounts_owner_id_users", "accounts", type_="foreignkey"
    )
    op.drop_column("accounts", "owner_id")

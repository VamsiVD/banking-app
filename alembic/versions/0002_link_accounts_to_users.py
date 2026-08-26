"""Link accounts to users: accounts.owner_id -> users.id.

Revision ID: 0002_link_accounts_to_users
Revises: 0001_initial
Create Date: 2026-08-26

Deliberately self-contained: no imports from `app`, same reasoning as
0001_initial — a migration is a snapshot of one moment in the schema and has
to keep replaying correctly years later.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_link_accounts_to_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("owner_id", sa.String(length=255), nullable=False),
    )
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

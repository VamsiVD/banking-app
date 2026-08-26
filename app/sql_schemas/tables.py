"""SQLAlchemy tables — the database's shape.

Kept separate from `schemas/models.py`, which stays purely Pydantic. Two mappings
of the same concepts, on purpose: Pydantic validates what crosses the API
boundary, these describe what the database stores and enforce it a second time in
SQL. `core/store.py` and the repositories convert between them, and they are the
only files that do.

Where the two disagree, the database wins, because it is the one that survives a
restart.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.api_schemas.account_schema import AccountStatus, AccountType
from app.api_schemas.transaction_schema import TransactionType

# Deterministic constraint names. Without this Postgres invents them, and a
# constraint violation error has nothing stable to name.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enum(python_enum, name: str) -> Enum:
    """A VARCHAR + CHECK column rather than a native Postgres ENUM type.

    Adding a value to a native enum needs ALTER TYPE, which historically could not
    run inside a transaction and still makes for an awkward migration. Widening a
    CHECK constraint is one ordinary line. We expect to add account types.
    """
    return Enum(
        python_enum,
        name=name,
        native_enum=False,
        # Store the member's value ("checking"), not its Python name. They happen
        # to match today; this keeps them matching if one ever diverges.
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
        # SQLAlchemy defaults this to False, which would leave a bare VARCHAR that
        # accepts "savngs" without complaint. The whole reason to prefer VARCHAR
        # over a native enum is that the CHECK is easy to widen -- not that it is
        # absent.
        create_constraint=True,
    )


class AccountRow(Base):
    __tablename__ = "accounts"

    # The account number is the key; there is no surrogate id. That is a decision
    # the API already made — it is the value in every URL path — so the database
    # follows it rather than inventing a second identity for the same thing.
    account_number: Mapped[str] = mapped_column(String(34), primary_key=True)
    account_holder_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        _enum(AccountType, "account_type"), nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        _enum(AccountStatus, "account_status"), nullable=False
    )
    # NUMERIC, never FLOAT. 18 digits with 2 after the point matches models.Money.
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    date_opened: Mapped[date] = mapped_column(Date, nullable=False)
    # Who owns the account. NOT NULL: a web account with no bank account is
    # normal, a bank account with no owner is not.
    owner_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        # The API refuses to overdraw an account. So does the database now — this
        # holds even against a stray UPDATE from a psql prompt.
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_is_iso_4217"),
        Index("ix_accounts_owner_id", "owner_id"),
    )


class TransactionRow(Base):
    """One immutable ledger entry.

    Append-only is enforced by not exposing any way to update or delete: see
    ledger.py, which has `record` and three readers and nothing else.
    """

    __tablename__ = "transactions"

    # uuid4().hex — 32 characters, no dashes. Stored as text to match the `str`
    # the Pydantic model already declares.
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_number: Mapped[str] = mapped_column(
        String(34), ForeignKey("accounts.account_number"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        _enum(TransactionType, "transaction_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    # The other side of a transfer. Deliberately NOT a foreign key: a counterparty
    # may one day be an account at another bank, and a constraint here would also
    # block ever deleting an account that has appeared in someone else's history.
    counterparty: Mapped[str | None] = mapped_column(String(34), nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        # Direction is carried by `type`; an amount is always positive. "A deposit
        # of -50" should be unrepresentable, not merely discouraged.
        CheckConstraint("amount > 0", name="amount_positive"),
        # The statements router pages one account's history in time order. This is
        # the index that query needs.
        Index("ix_transactions_account_number_timestamp", "account_number", "timestamp"),
    )

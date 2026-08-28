"""The `subscriptions` table.

One table for every user's subscriptions, scoped by `owner_id` — not one table
per user. A table per user would mean a schema migration on every signup and
no way to run one query across everyone's spending.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.api_schemas.subscription_schema import BillingCycle
from app.sql_schemas.tables import Base, _enum


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        _enum(BillingCycle, "billing_cycle"), nullable=False
    )
    next_billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Who this subscription belongs to. Set from the authenticated user, never
    # from the request body — see SubscriptionCreate.
    owner_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_is_iso_4217"),
        Index("ix_subscriptions_owner_id", "owner_id"),
    )

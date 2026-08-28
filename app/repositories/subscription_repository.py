"""Subscription records, backed by PostgreSQL.

Mirrors user_repository.py / admin_repository.py: a thin class over
SQLAlchemy, the only file that knows subscriptions are in SQL. Every read here
is scoped by owner_id — there is no "get any subscription by id" without it,
so one user's tracker can never surface another's.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.store import transaction
from app.db import current_session
from app.api_schemas.subscription_schema import Subscription, SubscriptionCreate
from app.sql_schemas.subscriptions import SubscriptionRow


def _to_model(row: SubscriptionRow) -> Subscription:
    return Subscription(
        id=row.id,
        name=row.name,
        amount=row.amount,
        currency=row.currency,
        billing_cycle=row.billing_cycle,
        next_billing_date=row.next_billing_date,
        owner_id=row.owner_id,
        created_at=row.created_at,
    )


class SubscriptionRepository:
    def create(self, owner_id: str, data: SubscriptionCreate) -> Subscription:
        row = SubscriptionRow(
            id=uuid4().hex,
            name=data.name,
            amount=data.amount,
            currency=data.currency,
            billing_cycle=data.billing_cycle,
            next_billing_date=data.next_billing_date,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        )
        with transaction():
            session = current_session()
            session.add(row)
            session.flush()
        return _to_model(row)

    def get_for_owner(self, subscription_id: str, owner_id: str) -> Subscription | None:
        row = current_session().scalars(
            select(SubscriptionRow)
            .where(
                SubscriptionRow.id == subscription_id,
                SubscriptionRow.owner_id == owner_id,
            )
            .execution_options(populate_existing=True)
        ).one_or_none()
        return _to_model(row) if row is not None else None

    def list_for_owner(self, owner_id: str) -> list[Subscription]:
        rows = current_session().scalars(
            select(SubscriptionRow)
            .where(SubscriptionRow.owner_id == owner_id)
            .order_by(SubscriptionRow.next_billing_date)
        ).all()
        return [_to_model(row) for row in rows]

    def delete_for_owner(self, subscription_id: str, owner_id: str) -> bool:
        with transaction():
            session = current_session()
            row = session.scalars(
                select(SubscriptionRow).where(
                    SubscriptionRow.id == subscription_id,
                    SubscriptionRow.owner_id == owner_id,
                )
            ).one_or_none()
            if row is None:
                return False
            session.delete(row)
            session.flush()
            return True


# importer gets this same instance
subscription_repository = SubscriptionRepository()

"""Subscription records, backed by the standalone subscription-tracker service.

That service (a separate Lambda API with its own Supabase Postgres) is the
source of truth now — this repository keeps no rows of its own, just the
translation between our field names/shapes and its wire format.

Its PATCH and DELETE routes take only a uuid; they don't check who owns the
row. So the ownership guarantee this app promises — one user can never touch
another's subscription — is enforced here instead: every write first confirms
the id shows up in the owner's own list before touching it, the same thing a
`WHERE owner_id = ...` clause used to get us for free.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.api_schemas.subscription_schema import BillingCycle, Subscription, SubscriptionCreate
from app.clients import subscription_tracker_client as client

# Months per billing cycle, for rolling a start date forward. Weekly is handled
# separately below since it doesn't divide evenly into months.
_CYCLE_MONTHS = {BillingCycle.monthly: 1, BillingCycle.yearly: 12}


def _to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _from_cents(amount: int) -> Decimal:
    return (Decimal(amount) / 100).quantize(Decimal("0.01"))


def _to_start_date(value: date) -> str:
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _from_start_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp so "Jan 31 + 1 month" lands on Feb 28/29, not an invalid Feb 31.
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _next_occurrence(start: date, cycle: BillingCycle, today: date) -> date:
    """The next billing date on or after `today`, given the original start date.

    The service only stores the original `start_date` — it doesn't roll it
    forward as cycles pass. So a subscription started months ago would show a
    "next billing date" stuck in the past unless we advance it here, live,
    every time a subscription is read.
    """
    if start >= today:
        return start

    if cycle is BillingCycle.weekly:
        weeks_elapsed = (today - start).days // 7
        candidate = start + timedelta(weeks=weeks_elapsed)
        while candidate < today:
            candidate += timedelta(weeks=1)
        return candidate

    step = _CYCLE_MONTHS[cycle]
    months_elapsed = (today.year - start.year) * 12 + (today.month - start.month)
    periods_elapsed = max(months_elapsed // step, 0)
    candidate = _add_months(start, periods_elapsed * step)
    while candidate < today:
        candidate = _add_months(candidate, step)
    return candidate


def _to_payload(owner_id: str, data: SubscriptionCreate) -> dict:
    return {
        "name": data.name,
        "type": data.billing_cycle.value,
        "amount": _to_cents(data.amount),
        # What the caller picks in the "next billing date" field becomes the
        # schedule's anchor point — later reads roll it forward from here.
        "start_date": _to_start_date(data.next_billing_date),
        "currency": data.currency,
        "owner_id": owner_id,
    }


def _to_model(row: dict) -> Subscription:
    cycle = BillingCycle(row["type"])
    start = _from_start_date(row["start_date"])
    return Subscription(
        id=row["uuid"],
        name=row["name"],
        amount=_from_cents(row["amount"]),
        currency=row["currency"],
        billing_cycle=cycle,
        next_billing_date=_next_occurrence(start, cycle, date.today()),
        owner_id=row["owner_id"],
    )


class SubscriptionRepository:
    def create(self, owner_id: str, data: SubscriptionCreate) -> Subscription:
        row = client.create(_to_payload(owner_id, data))
        return _to_model(row)

    def get_for_owner(self, subscription_id: str, owner_id: str) -> Subscription | None:
        for row in client.list_for_owner(owner_id):
            if row["uuid"] == subscription_id:
                return _to_model(row)
        return None

    def list_for_owner(self, owner_id: str) -> list[Subscription]:
        models = [_to_model(row) for row in client.list_for_owner(owner_id)]
        return sorted(models, key=lambda s: s.next_billing_date)

    def delete_for_owner(self, subscription_id: str, owner_id: str) -> bool:
        if self.get_for_owner(subscription_id, owner_id) is None:
            return False
        client.delete(subscription_id)
        return True


# importer gets this same instance
subscription_repository = SubscriptionRepository()

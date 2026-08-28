"""Subscription domain: types, create request, and stored/returned shape."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.api_schemas.primitives import PositiveMoney, Currency


class BillingCycle(str, Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionCreate(BaseModel):
    """Request body for adding a subscription.

    No owner_id here: the owner is whoever the access token says is making the
    request, not something the client gets to assert about itself.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    amount: PositiveMoney
    currency: Currency = "USD"
    billing_cycle: BillingCycle
    next_billing_date: date


class Subscription(SubscriptionCreate):
    """A subscription as stored and returned by the API."""

    id: str
    owner_id: str
    created_at: datetime

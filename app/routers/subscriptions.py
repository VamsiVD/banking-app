"""Subscriptions tracker — create, list, fetch, delete.

Every endpoint requires login; every read and write is scoped to the caller's
own subscriptions via owner_id from the token, never from the request body or
the URL. There is no way to name someone else's subscription id and get
anything back but a 404.
"""

from fastapi import APIRouter, Depends

from app.core.auth_guard import get_current_user
from app.api_schemas.subscription_schema import Subscription, SubscriptionCreate
from app.services import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=Subscription, status_code=201)
def create_subscription(
    data: SubscriptionCreate, user=Depends(get_current_user)
) -> Subscription:
    return subscription_service.create_subscription(user["id"], data)


@router.get("/", response_model=list[Subscription])
def list_subscriptions(user=Depends(get_current_user)) -> list[Subscription]:
    return subscription_service.list_subscriptions(user["id"])


@router.get("/{subscription_id}", response_model=Subscription)
def get_subscription(
    subscription_id: str, user=Depends(get_current_user)
) -> Subscription:
    return subscription_service.get_subscription(subscription_id, user["id"])


@router.delete("/{subscription_id}")
def delete_subscription(
    subscription_id: str, user=Depends(get_current_user)
) -> dict[str, str]:
    subscription_service.delete_subscription(subscription_id, user["id"])
    return {"message": f"Subscription {subscription_id} deleted"}

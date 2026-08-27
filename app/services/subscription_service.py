from app.api_schemas.subscription_schema import Subscription, SubscriptionCreate
from app.errors import SubscriptionNotFound
from app.repositories.subscription_repository import subscription_repository


def create_subscription(owner_id: str, data: SubscriptionCreate) -> Subscription:
    return subscription_repository.create(owner_id, data)


def list_subscriptions(owner_id: str) -> list[Subscription]:
    return subscription_repository.list_for_owner(owner_id)


def get_subscription(subscription_id: str, owner_id: str) -> Subscription:
    subscription = subscription_repository.get_for_owner(subscription_id, owner_id)
    if subscription is None:
        raise SubscriptionNotFound(f"No subscription with id {subscription_id!r}.")
    return subscription


def delete_subscription(subscription_id: str, owner_id: str) -> None:
    if not subscription_repository.delete_for_owner(subscription_id, owner_id):
        raise SubscriptionNotFound(f"No subscription with id {subscription_id!r}.")

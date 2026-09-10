"""HTTP client for the standalone subscription-tracker service.

A separate Lambda-hosted API with its own Supabase Postgres — this app keeps no
subscription rows of its own any more. This is the only file that knows the
service's base URL or wire shape; app/repositories/subscription_repository.py
translates between that shape and our own field names.
"""

import httpx

from app.config import get_settings
from app.errors import SubscriptionServiceUnavailable

_TIMEOUT = 10.0


def _request(method: str, path: str, **kwargs) -> httpx.Response:
    base_url = get_settings().SUBSCRIPTION_TRACKER_BASE_URL
    try:
        response = httpx.request(method, f"{base_url}{path}", timeout=_TIMEOUT, **kwargs)
    except httpx.HTTPError as exc:
        raise SubscriptionServiceUnavailable(
            f"Could not reach the subscription service: {exc}"
        ) from exc
    if response.is_error:
        raise SubscriptionServiceUnavailable(
            f"Subscription service returned {response.status_code} for "
            f"{method} {path}."
        )
    return response


def create(payload: dict) -> dict:
    return _request("POST", "/subscriptions", json=payload).json()


def list_for_owner(owner_id: str) -> list[dict]:
    # The service returns `null`, not `[]`, when the owner has nothing yet.
    return _request("GET", f"/subscriptions/{owner_id}").json() or []


def delete(subscription_id: str) -> None:
    _request("DELETE", f"/subscriptions/{subscription_id}")

"""Tests for the /subscriptions tracker: create, list, fetch, delete.

Every endpoint requires login and is scoped to the caller's own subscriptions
via owner_id from the token — the important cases here are less "does CRUD
work" and more "can one user ever see or touch another user's subscription."
"""

import pytest

from conftest import DEFAULT_OWNER_ID
from app.clients import subscription_tracker_client


class _FakeSubscriptionService:
    """Stands in for the real Lambda service: same wire shape, in memory.

    Also mirrors its one important quirk — delete takes only a uuid, no owner
    check — so the cross-owner tests below prove the repository enforces
    ownership itself, not the fake.
    """

    def __init__(self):
        self._rows: dict[str, dict] = {}
        self._next_id = 1

    def create(self, payload: dict) -> dict:
        row = {**payload, "uuid": f"fake-{self._next_id}"}
        self._next_id += 1
        self._rows[row["uuid"]] = row
        return dict(row)

    def list_for_owner(self, owner_id: str) -> list[dict]:
        return [dict(row) for row in self._rows.values() if row["owner_id"] == owner_id]

    def delete(self, subscription_id: str) -> None:
        self._rows.pop(subscription_id, None)


@pytest.fixture(autouse=True)
def fake_subscription_service(monkeypatch):
    """Every test in this file hits the fake instead of the real service."""
    fake = _FakeSubscriptionService()
    monkeypatch.setattr(subscription_tracker_client, "create", fake.create)
    monkeypatch.setattr(subscription_tracker_client, "list_for_owner", fake.list_for_owner)
    monkeypatch.setattr(subscription_tracker_client, "delete", fake.delete)
    return fake


def err(response) -> str:
    return response.json()["error"]["code"]


def new_subscription(name="Netflix", amount="15.99", currency="USD",
                      billing_cycle="monthly", next_billing_date="2026-09-01", **extra):
    return {
        "name": name,
        "amount": amount,
        "currency": currency,
        "billing_cycle": billing_cycle,
        "next_billing_date": next_billing_date,
        **extra,
    }


def other_user_headers(client) -> dict[str, str]:
    """A second, distinct logged-in user, for cross-owner isolation tests."""
    email = "someone-else@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse", "full_name": "Someone Else"},
    )
    r = client.post("/auth/login", json={"email": email, "password": "correct-horse"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------


def test_anonymous_request_is_401(client):
    assert client.get("/subscriptions/").status_code == 401


# --------------------------------------------------------------------------
# create
# --------------------------------------------------------------------------


def test_create_persists_the_subscription(client, auth_headers):
    r = client.post("/subscriptions/", json=new_subscription(), headers=auth_headers)

    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Netflix"
    assert body["amount"] == "15.99"
    assert body["owner_id"] == DEFAULT_OWNER_ID
    assert body["id"]


def test_a_non_positive_amount_is_refused(client, auth_headers):
    r = client.post(
        "/subscriptions/", json=new_subscription(amount="0.00"), headers=auth_headers
    )

    assert r.status_code == 422


def test_an_unknown_billing_cycle_is_refused(client, auth_headers):
    r = client.post(
        "/subscriptions/", json=new_subscription(billing_cycle="daily"), headers=auth_headers
    )

    assert r.status_code == 422


def test_an_owner_id_in_the_body_is_rejected(client, auth_headers):
    """owner_id comes from the token, not the body — sending one trips extra="forbid"."""
    r = client.post(
        "/subscriptions/",
        json=new_subscription(owner_id="someone-else@example.com"),
        headers=auth_headers,
    )

    assert r.status_code == 422


# --------------------------------------------------------------------------
# list / fetch
# --------------------------------------------------------------------------


def test_list_is_empty_before_creating_any(client, auth_headers):
    assert client.get("/subscriptions/", headers=auth_headers).json() == []


def test_list_returns_only_the_caller_s_own_subscriptions(client, auth_headers):
    client.post("/subscriptions/", json=new_subscription(name="Netflix"), headers=auth_headers)

    other_headers = other_user_headers(client)
    client.post(
        "/subscriptions/", json=new_subscription(name="Spotify"), headers=other_headers
    )

    names = [s["name"] for s in client.get("/subscriptions/", headers=auth_headers).json()]

    assert names == ["Netflix"]


def test_fetching_a_subscription_by_id(client, auth_headers):
    created = client.post(
        "/subscriptions/", json=new_subscription(), headers=auth_headers
    ).json()

    r = client.get(f"/subscriptions/{created['id']}", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_fetching_an_unknown_id_is_404(client, auth_headers):
    r = client.get("/subscriptions/NOPE", headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "subscription_not_found"


def test_fetching_someone_else_s_subscription_is_404(client, auth_headers):
    """Not 403 — a caller should not be able to distinguish "not yours" from
    "does not exist" by probing ids."""
    created = client.post(
        "/subscriptions/", json=new_subscription(), headers=auth_headers
    ).json()

    other_headers = other_user_headers(client)
    r = client.get(f"/subscriptions/{created['id']}", headers=other_headers)

    assert r.status_code == 404
    assert err(r) == "subscription_not_found"


# --------------------------------------------------------------------------
# delete
# --------------------------------------------------------------------------


def test_delete_removes_a_subscription(client, auth_headers):
    created = client.post(
        "/subscriptions/", json=new_subscription(), headers=auth_headers
    ).json()

    assert client.delete(f"/subscriptions/{created['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/subscriptions/{created['id']}", headers=auth_headers).status_code == 404


def test_deleting_an_unknown_id_is_404(client, auth_headers):
    r = client.delete("/subscriptions/NOPE", headers=auth_headers)

    assert r.status_code == 404
    assert err(r) == "subscription_not_found"


def test_deleting_someone_else_s_subscription_is_404_and_does_not_delete_it(client, auth_headers):
    created = client.post(
        "/subscriptions/", json=new_subscription(), headers=auth_headers
    ).json()

    other_headers = other_user_headers(client)
    r = client.delete(f"/subscriptions/{created['id']}", headers=other_headers)

    assert r.status_code == 404
    assert client.get(f"/subscriptions/{created['id']}", headers=auth_headers).status_code == 200

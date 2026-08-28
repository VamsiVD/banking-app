"""Shared test fixtures.

Runs against a real PostgreSQL database — the one named by TEST_DATABASE_URL,
never the development one. The suite truncates tables between cases, so pointing
it at DATABASE_URL would delete whatever you were working with; the guard below
refuses to start if the two match.

    docker compose up -d --wait
    pytest

Accounts are seeded straight into the store rather than created through
POST /accounts, because that endpoint belongs to the accounts slice and does not
exist yet. When it lands, `make_account` is the one place to switch over.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import db
from app.core import store
from app.config import get_settings
from app.core import security
from app.main import app
from app.repositories.user_repository import user_repository
from app.api_schemas.account_schema import BankAccount

# Accounts carry a foreign key to `users`. This is the owner every account
# fixture/helper defaults to; ensure_owner() creates it lazily since
# clean_state truncates users between tests.
DEFAULT_OWNER_ID = "owner@example.com"
DEFAULT_ADMIN_ID = "admin@example.com"


def ensure_owner(owner_id: str = DEFAULT_OWNER_ID) -> None:
    if user_repository.get_by_email(owner_id) is None:
        user_repository.create(owner_id, "Test Owner", security.hash_password("password123"))


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Point the engine at the test database and bring its schema up to date.

    Session-scoped: creating tables once per run, not once per test.
    """
    settings = get_settings()
    test_url = settings.TEST_DATABASE_URL

    if not test_url:
        pytest.exit(
            "TEST_DATABASE_URL is not set. Copy .env.example to .env "
            "(the default points at the banking_test database).",
            returncode=1,
        )
    if test_url == settings.DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL and DATABASE_URL are the same database. The suite "
            "truncates tables between tests and would erase your development "
            "data. Point them at different databases.",
            returncode=1,
        )

    db.configure(test_url)
    db.init_db()

    yield

    db.get_engine().dispose()


@pytest.fixture(autouse=True)
def db_session(_database):
    """A session for the test body itself.

    Requests made through `client` get their own session from the middleware, so
    a test that seeds data and then calls an endpoint is genuinely crossing a
    connection boundary — which is what makes the concurrency tests below mean
    anything.
    """
    with db.session_scope() as session:
        yield session


@pytest.fixture(autouse=True)
def clean_state(db_session):
    """Tables persist between tests, so state leaks unless cleared."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Log the default test owner in and hand back a ready-to-use auth header."""
    ensure_owner()
    r = client.post(
        "/auth/login",
        json={"email": DEFAULT_OWNER_ID, "password": "password123"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    """The same, for an administrator — the caller who may change an account.

    Registers on the way in rather than relying on a seeded row, because the
    fixtures truncate between cases.
    """
    client.post(
        "/admin/register",
        json={
            "email": DEFAULT_ADMIN_ID,
            "password": "password123",
            "full_name": "Test Admin",
        },
    )
    r = client.post(
        "/admin/login",
        json={"email": DEFAULT_ADMIN_ID, "password": "password123"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_account():
    def _make(
        account_number: str = "ACC-1",
        balance: str = "100.00",
        currency: str = "USD",
        status: str = "active",
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> BankAccount:
        ensure_owner(owner_id)
        return store.add(
            BankAccount(
                account_number=account_number,
                account_holder_name="Test Holder",
                account_type="checking",
                status=status,
                balance=Decimal(balance),
                currency=currency,
                date_opened=date.today(),
                owner_id=owner_id,
            )
        )

    return _make

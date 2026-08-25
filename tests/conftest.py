"""Shared test fixtures.

Accounts are seeded straight into the store rather than created through
POST /accounts, because that endpoint belongs to the accounts slice and does not
exist yet. When it lands, `make_account` is the one place to switch over.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import ledger, store
from app.main import app
from app.models import BankAccount


@pytest.fixture(autouse=True)
def clean_state():
    """The store is module-level, so state leaks between tests unless cleared."""
    store.reset()
    ledger.reset()
    yield
    store.reset()
    ledger.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_account():
    def _make(
        account_number: str = "ACC-1",
        balance: str = "100.00",
        currency: str = "USD",
        status: str = "active",
    ) -> BankAccount:
        return store.add(
            BankAccount(
                account_number=account_number,
                account_holder_name="Test Holder",
                account_type="checking",
                status=status,
                balance=Decimal(balance),
                currency=currency,
                date_opened=date.today(),
            )
        )

    return _make

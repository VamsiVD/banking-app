"""Pure transfer rules — no store access, no I/O.

Each function takes values already fetched by the caller and either returns
quietly or raises. Kept separate from account_repository so the policy
question ("what makes a transfer valid") stays independent of "how do we fetch
an account".
"""

from decimal import Decimal

from app.errors import AccountNotActive, CurrencyMismatch, InsufficientFunds
from app.api_schemas.account_schema import AccountStatus, BankAccount


def assert_active(account: BankAccount) -> None:
    """Only active accounts can move money.

    Deliberately local to transfers rather than shared with the deposit/withdraw
    slice. The status rule is a policy question that can legitimately differ per
    operation — plenty of banks accept credits into a frozen account while
    refusing debits — so a shared rule would force one answer on both.
    """
    if account.status is not AccountStatus.active:
        raise AccountNotActive(
            f"Account {account.account_number!r} is {account.status.value}; "
            "only active accounts can move money."
        )


def assert_same_currency(source: BankAccount, destination: BankAccount) -> None:
    # No FX here. Converting currencies is a rate decision, and this API has
    # no rate source it could honestly use.
    if source.currency != destination.currency:
        raise CurrencyMismatch(
            f"Cannot transfer between {source.currency} and "
            f"{destination.currency}; this API does no currency conversion."
        )


def assert_sufficient_funds(source: BankAccount, amount: Decimal) -> None:
    if source.balance < amount:
        raise InsufficientFunds(
            f"Account {source.account_number!r} holds {source.balance} "
            f"{source.currency}; cannot transfer {amount}."
        )

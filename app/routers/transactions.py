"""Money movement — deposits, withdrawals, transfers.

Owner: utoker
Branch: feat/transactions

Every endpoint here does its validation first and its mutation second, all inside
one `store.transaction()` block. That ordering matters: the block is not a
rollback, so a half-applied change cannot be undone. Nothing is written until
every reason to refuse has been ruled out.

Amounts appear in JSON as strings ("40.00"), not numbers. Pydantic serializes
Decimal that way on purpose — a JSON number is a float, which is exactly the
precision loss we are avoiding.
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app import ledger, store
from app.errors import AccountNotActive, AccountNotFound, CurrencyMismatch, InsufficientFunds
from app.models import (
    AccountNumber,
    AccountStatus,
    BankAccount,
    PositiveMoney,
    Transaction,
    TransactionType,
)

# No prefix: this router owns paths under both /accounts and /transfers.
router = APIRouter(tags=["transactions"])


class MovementRequest(BaseModel):
    """Body for a deposit or a withdrawal."""

    model_config = ConfigDict(extra="forbid")

    amount: PositiveMoney
    description: str | None = Field(default=None, max_length=200)


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_account_number: AccountNumber
    to_account_number: AccountNumber
    amount: PositiveMoney
    description: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _reject_self_transfer(self) -> "TransferRequest":
        # A 422 rather than a domain error: this is a malformed request, knowable
        # from the body alone without consulting any account.
        if self.from_account_number == self.to_account_number:
            raise ValueError("from_account_number and to_account_number must differ.")
        return self


class TransferResult(BaseModel):
    """Both sides of a transfer. One movement, two ledger entries."""

    debit: Transaction
    credit: Transaction


def _active_account(account_number: str) -> BankAccount:
    """Fetch an account that is allowed to move money, or raise.

    Call inside a store.transaction() block — the account it returns is a live
    reference, and the guarantee that it is still active only holds under the lock.
    """
    account = store.get(account_number)
    if account is None:
        raise AccountNotFound(f"No account with number {account_number!r}.")
    if account.status is not AccountStatus.active:
        raise AccountNotActive(
            f"Account {account_number!r} is {account.status.value}; "
            "only active accounts can move money."
        )
    return account


def _with_balance(account: BankAccount, balance) -> BankAccount:
    """Return a copy of `account` at a new balance, and store it.

    A copy rather than an in-place `account.balance = ...` because store.get()
    hands back the live object: mutating it writes to the store whether or not
    store.put() is ever reached. Going through put() keeps the write in one
    place, which is where a real database call will eventually go.
    """
    updated = account.model_copy(update={"balance": balance})
    return store.put(updated)


@router.post(
    "/accounts/{account_number}/deposit",
    response_model=Transaction,
    status_code=201,
    summary="Deposit funds into an account",
)
def deposit(account_number: str, body: MovementRequest) -> Transaction:
    with store.transaction():
        account = _active_account(account_number)
        updated = _with_balance(account, account.balance + body.amount)
        return ledger.record(
            updated.account_number,
            TransactionType.deposit,
            body.amount,
            updated.currency,
            updated.balance,
            description=body.description,
        )


@router.post(
    "/accounts/{account_number}/withdraw",
    response_model=Transaction,
    status_code=201,
    summary="Withdraw funds from an account",
)
def withdraw(account_number: str, body: MovementRequest) -> Transaction:
    with store.transaction():
        account = _active_account(account_number)
        if account.balance < body.amount:
            raise InsufficientFunds(
                f"Account {account_number!r} holds {account.balance} "
                f"{account.currency}; cannot withdraw {body.amount}."
            )
        updated = _with_balance(account, account.balance - body.amount)
        return ledger.record(
            updated.account_number,
            TransactionType.withdrawal,
            body.amount,
            updated.currency,
            updated.balance,
            description=body.description,
        )


@router.post(
    "/transfers",
    response_model=TransferResult,
    status_code=201,
    summary="Transfer funds between two accounts",
)
def transfer(body: TransferRequest) -> TransferResult:
    with store.transaction():
        source = _active_account(body.from_account_number)
        destination = _active_account(body.to_account_number)

        # No FX here. Converting currencies is a rate decision, and this API has
        # no rate source it could honestly use.
        if source.currency != destination.currency:
            raise CurrencyMismatch(
                f"Cannot transfer between {source.currency} and "
                f"{destination.currency}; this API does no currency conversion."
            )
        if source.balance < body.amount:
            raise InsufficientFunds(
                f"Account {source.account_number!r} holds {source.balance} "
                f"{source.currency}; cannot transfer {body.amount}."
            )

        # Every refusal is now behind us, so both sides can be written.
        source = _with_balance(source, source.balance - body.amount)
        destination = _with_balance(destination, destination.balance + body.amount)

        debit = ledger.record(
            source.account_number,
            TransactionType.transfer_out,
            body.amount,
            source.currency,
            source.balance,
            counterparty=destination.account_number,
            description=body.description,
        )
        credit = ledger.record(
            destination.account_number,
            TransactionType.transfer_in,
            body.amount,
            destination.currency,
            destination.balance,
            counterparty=source.account_number,
            description=body.description,
        )
        return TransferResult(debit=debit, credit=credit)

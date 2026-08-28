"""Transfers controller — see services/transfer_service.py for the logic."""

from fastapi import APIRouter, Depends, Query

from app.api_schemas.transfer_schema import (
    TransferPage,
    TransferRequest,
    TransferResult,
    TransferSummary,
)
from app.core.auth_guard import get_current_principal, get_current_user
from app.services import transfer_service

router = APIRouter(tags=["transfers"])


@router.post(
    "/transfers",
    response_model=TransferResult,
    status_code=201,
    summary="Transfer funds between two accounts",
)
def transfer(body: TransferRequest, user=Depends(get_current_user)) -> TransferResult:
    return transfer_service.execute_transfer(body)


@router.get(
    "/transfers",
    response_model=TransferPage,
    summary="List transfers, newest first",
)
def list_transfers(
    account_number: str | None = Query(
        default=None,
        description="Only transfers involving this account, sent or received.",
    ),
    limit: int = Query(default=50, ge=1, le=transfer_service.MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    caller=Depends(get_current_principal),
) -> TransferPage:
    return transfer_service.list_transfers(account_number, limit, offset)


@router.get(
    "/transfers/{transfer_id}",
    response_model=TransferSummary,
    summary="Fetch one transfer",
)
def get_transfer(transfer_id: str, caller=Depends(get_current_principal)) -> TransferSummary:
    return transfer_service.get_transfer(transfer_id)

"""Transfers controller — see services/transfer_service.py for the logic."""

from fastapi import APIRouter

from app.schemas.transfer_schema import TransferRequest, TransferResult
from app.services import transfer_service

router = APIRouter(tags=["transfers"])


@router.post(
    "/transfers",
    response_model=TransferResult,
    status_code=201,
    summary="Transfer funds between two accounts",
)
def transfer(body: TransferRequest) -> TransferResult:
    return transfer_service.execute_transfer(body)

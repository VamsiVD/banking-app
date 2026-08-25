"""One error shape for the whole API.

Every failure a client can cause comes back as:

    {"error": {"code": "insufficient_funds", "message": "..."}}

Raise these from routers instead of HTTPException, so the codes stay a closed
set the client can actually branch on. Add a subclass here when you need a new
one rather than inventing a shape in your own router.
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AccountNotFound(AppError):
    status_code = 404
    code = "account_not_found"


class DuplicateAccount(AppError):
    status_code = 409
    code = "duplicate_account"


class InsufficientFunds(AppError):
    status_code = 409
    code = "insufficient_funds"


class AccountNotActive(AppError):
    status_code = 409
    code = "account_not_active"


class CurrencyMismatch(AppError):
    status_code = 409
    code = "currency_mismatch"


class AccountHasHistory(AppError):
    """Deleting an account that has ledger entries.

    A ledger is only auditable if its entries outlive nothing. Closing an account
    is a status change; deleting one that has moved money is not offered.
    """

    status_code = 409
    code = "account_has_history"


class EmailAlreadyRegistered(AppError):
    status_code = 409
    code = "email_already_registered"


class InvalidCredentials(AppError):
    status_code = 401
    code = "invalid_credentials"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    # FastAPI's own 422 body has a different shape; reshape it so clients only
    # ever parse one envelope.
    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request body or parameters failed validation.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

"""Application entry point.

Run it with:  uvicorn app.main:app --reload
Interactive docs:  http://127.0.0.1:8000/docs

Every router is registered here already, including the ones that are still empty.
That is on purpose: it means nobody has to edit this file to add their endpoints,
so three people can work in parallel without colliding on it.
"""

from fastapi import FastAPI

from app.errors import install_error_handlers
from app.routers import accounts, queries, statements, transactions, BankProfile
from app.routers import accounts, queries, statements, transactions, transfers

app = FastAPI(
    title="Banking API",
    version="0.1.0",
    description="Training project. In-memory store, no database, no auth.",
)

install_error_handlers(app)

app.include_router(BankProfile.router)
app.include_router(accounts.router)
app.include_router(queries.router)
app.include_router(transactions.router)
app.include_router(statements.router)
app.include_router(transfers.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check. Also the smoke test that the app boots at all."""
    return {"status": "ok"}

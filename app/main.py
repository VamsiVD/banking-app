"""Application entry point.

Run it with:  uvicorn app.main:app --reload
Interactive docs:  http://127.0.0.1:8000/docs

Needs a database. First time, or after pulling:

    cp .env.example .env          # once
    docker compose up -d --wait
    python -m scripts.seed        # optional demo accounts

Tables are created automatically on startup from `app/tables.py`. That only adds
tables that do not exist yet — altering an existing one needs a manual ALTER.

Every router is registered here already, including the ones that are still empty.
That is on purpose: it means nobody has to edit this file to add their endpoints,
so several people can work in parallel without colliding on it.
"""

import sys

from dotenv import load_dotenv

# Before any app.* import, so app.config sees DATABASE_URL from .env.
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import install_error_handlers
from app.routers import (
    accounts,
    auth,
    queries,
    statements,
    transactions,
    transfers,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail here, with an instruction, rather than on the first request with a
    # connection-refused traceback that says nothing about what to do next.
    try:
        db.check_connection()
    except SQLAlchemyError as exc:
        print( 
            "\nCannot reach PostgreSQL.\n"
            "  1. Is it running?      docker compose up -d --wait\n"
            "  2. Is .env present?    cp .env.example .env\n"
            f"\nUnderlying error: {exc}\n",
            file=sys.stderr,
        )
        raise
    db.init_db()
    yield
    db.get_engine().dispose()


app = FastAPI(
    title="Banking API",
    version="0.2.0",
    description="Training project. PostgreSQL-backed.",
    lifespan=lifespan,
)

# Gives every request a session and cleans it up afterwards. Added before the
# routers so it wraps all of them.
app.add_middleware(db.SessionMiddleware)

install_error_handlers(app)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(queries.router)
app.include_router(transactions.router)
app.include_router(statements.router)
app.include_router(transfers.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check. Also the smoke test that the app boots at all."""
    return {"status": "ok"}


@app.get("/health/db", tags=["meta"])
def health_db() -> JSONResponse:
    """Readiness check: is the database actually reachable right now?

    Separate from /health on purpose. /health answers "did the process start",
    which stays true while Postgres is down; this one answers "can I serve a
    request", which does not.
    """
    try:
        db.current_session().execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": f"Cannot reach the database: {exc.__class__.__name__}",
                }
            },
        )
    return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})

"""Engine, session, and the transaction primitive.

This file exists so `store.py` and `ledger.py` can keep the exact function
signatures they had when the store was a dict. Routers never import it — they go
on calling `store.get()` and `with store.transaction():` as before.

The session lives in a ContextVar, set once per request by `SessionMiddleware`.
That middleware is deliberately a raw ASGI class rather than a Starlette
`BaseHTTPMiddleware`: BaseHTTPMiddleware runs the rest of the app in a separate
anyio task, which puts a context boundary between the middleware and the
endpoint. A raw ASGI middleware runs in the same task, so the ContextVar set here
is visible in the endpoint — including sync `def` endpoints, which FastAPI runs in
a threadpool that inherits a copy of the current context.

The one rule worth knowing: `transaction()` commits, the middleware does not.
Whatever is still open when a request ends is rolled back, so a handler that
raises after a partial write leaves nothing behind.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None

# The session for the request currently being handled.
_session: ContextVar[Session | None] = ContextVar("_session", default=None)

# How many nested `transaction()` blocks we are inside. Only the outermost one
# commits. The dict-backed store used a reentrant lock and got this for free;
# SQLAlchemy raises if you call begin() twice, so we count instead.
_depth: ContextVar[int] = ContextVar("_depth", default=0)


def configure(url: str | None = None, echo: bool | None = None) -> Engine:
    """Build (or rebuild) the engine. Returns it.

    Called automatically on first use with the settings from `.env`. Tests call it
    explicitly with TEST_DATABASE_URL before the first query.
    """
    global _engine, _session_factory

    settings = get_settings()
    if url is None:
        url = settings.DATABASE_URL
    if echo is None:
        echo = settings.SQL_ECHO

    if _engine is not None:
        _engine.dispose()

    _engine = create_engine(
        url,
        echo=echo,
        # A container restart or a laptop sleeping overnight leaves dead
        # connections in the pool; without this the next request gets the
        # corpse instead of a new connection.
        pool_pre_ping=True,
        # Supabase's transaction-mode pooler hands out a different physical
        # connection per statement, so a server-side prepared statement from
        # one call can vanish (or belong to someone else) by the next. Force
        # psycopg to skip preparing statements entirely.
        connect_args={"prepare_threshold": None},
    )
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        configure()
    assert _engine is not None
    return _engine


def new_session() -> Session:
    if _session_factory is None:
        configure()
    assert _session_factory is not None
    return _session_factory()


def current_session() -> Session:
    """The session for this request.

    Raises with an actionable message rather than returning None, because the
    failure mode it catches — calling the store outside a request, usually from a
    script or a test missing its fixture — is otherwise an AttributeError forty
    frames deep.
    """
    session = _session.get()
    if session is None:
        raise RuntimeError(
            "No database session in this context. A store/ledger call happened "
            "outside a request. In the app, SessionMiddleware provides the "
            "session; in tests, use the `db_session` fixture from conftest.py."
        )
    return session


@contextmanager
def session_scope(session: Session | None = None) -> Iterator[Session]:
    """Bind a session to this context for the duration of the block.

    Never commits. `transaction()` owns commits; anything still open at the end of
    a request is rolled back, so a half-finished write cannot leak into the next
    one.
    """
    owns = session is None
    if session is None:
        session = new_session()

    token = _session.set(session)
    depth_token = _depth.set(0)
    try:
        yield session
    finally:
        _depth.reset(depth_token)
        _session.reset(token)
        try:
            if session.in_transaction():
                session.rollback()
        finally:
            if owns:
                session.close()


@contextmanager
def transaction() -> Iterator[Session]:
    """Run a read-modify-write as one atomic unit. Reentrant.

    The outermost block commits on a clean exit and rolls back on any exception;
    nested blocks simply join it. That nesting is not hypothetical —
    `ledger.record()` opens one of these from inside the block `transfers.py`
    already holds, and both halves of a transfer plus their two ledger entries
    have to land or fail together.
    """
    session = current_session()
    depth = _depth.get()

    if depth > 0:
        # Already inside one. Join it: the outermost block decides the outcome.
        token = _depth.set(depth + 1)
        try:
            yield session
        finally:
            _depth.reset(token)
        return

    token = _depth.set(1)
    try:
        if not session.in_transaction():
            session.begin()
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        _depth.reset(token)


def in_transaction() -> bool:
    """True inside a `transaction()` block.

    `store.get()` uses this to decide whether to take a row lock: a bare read
    needs none, but a read that is about to become a write needs SELECT ... FOR
    UPDATE held until the block ends.
    """
    return _depth.get() > 0


def get_session() -> Session:
    """FastAPI dependency, for routers that want to write real queries.

    Filtering, sorting and paging belong in SQL, not in a Python loop over
    `store.list_all()`. Use it like any other dependency:

        @router.get("/accounts")
        def list_accounts(db: Session = Depends(get_session)):
            return db.scalars(select(AccountRow).limit(50)).all()

    It hands back the same session the store is using, so a query here sees
    uncommitted writes made earlier in the same request.
    """
    return current_session()


def check_connection() -> None:
    """Raise if the database is unreachable. Called at startup."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def init_db() -> None:
    """Create any tables from `app.tables` that do not exist yet.

    Only creates missing tables — it will not add a column to one that already
    exists. Changing an existing table needs a manual ALTER, run by hand.
    """
    from app.sql_schemas.tables import Base

    Base.metadata.create_all(get_engine())


class SessionMiddleware:
    """Give every HTTP request a session, and clean it up afterwards."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        # Lifespan and websocket scopes get no session; neither runs store code.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        with session_scope():
            await self.app(scope, receive, send)

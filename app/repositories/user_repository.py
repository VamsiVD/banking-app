"""User records, backed by PostgreSQL.

Same class, same two methods, same return type as the dict version; callers are
unchanged. Both methods hand back a plain `dict`, not an ORM row, because
`auth_service` reads `user["hashed_password"]` and `routers/auth.py` reads
`user["id"]`; returning rows would break both for no gain.

Registered users now survive a restart, which is the whole point.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.store import transaction
from app.db import current_session
from app.errors import EmailAlreadyRegistered
from app.sql_schemas.auth import UserRow


def _to_dict(row: UserRow) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "hashed_password": row.hashed_password,
        "created_at": row.created_at,
    }


class UserRepository:
    """Save and fetch user records. The only file that knows users are in SQL."""

    def get_by_email(self, email: str) -> dict | None:
        row = current_session().scalars(
            select(UserRow)
            .where(UserRow.email == email)
            .execution_options(populate_existing=True)
        ).one_or_none()
        return _to_dict(row) if row is not None else None

    def get_by_id(self, user_id: str) -> dict | None:
        # The id is the email, so this is the same lookup by another name.
        return self.get_by_email(user_id)

    def list_all(self) -> list[dict]:
        rows = current_session().scalars(
            select(UserRow).order_by(UserRow.email)
        ).all()
        return [_to_dict(row) for row in rows]

    def create(self, email: str, full_name: str, hashed_password: bytes) -> dict:
        """Insert a user.

        Raises EmailAlreadyRegistered on a duplicate. `register_user()` checks
        first, but two simultaneous registrations can both pass that check; the
        unique constraint is what actually decides, and translating it here means
        the loser still gets the clean 409 that `routers/auth.py` already handles.
        """
        row = UserRow(
            # The email doubles as the id, as it always has here.
            id=email,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
        )
        try:
            with transaction():
                session = current_session()
                session.add(row)
                session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyRegistered("email already registered") from exc
        return _to_dict(row)


# importer gets this same instance
user_repository = UserRepository()

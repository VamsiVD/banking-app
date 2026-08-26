"""Admin records, backed by PostgreSQL.

Mirrors `user_repository.py` exactly, against the separate `admins` table
instead of `users`. Kept as its own file/class rather than a shared base so an
admin lookup can never accidentally query the customer table, or vice versa.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.store import transaction
from app.db import current_session
from app.errors import EmailAlreadyRegistered
from app.sql_schemas.admin import AdminRow


def _to_dict(row: AdminRow) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "hashed_password": row.hashed_password,
        "created_at": row.created_at,
    }


class AdminRepository:
    """Save and fetch admin records. The only file that knows admins are in SQL."""

    def get_by_email(self, email: str) -> dict | None:
        row = current_session().scalars(
            select(AdminRow)
            .where(AdminRow.email == email)
            .execution_options(populate_existing=True)
        ).one_or_none()
        return _to_dict(row) if row is not None else None

    def get_by_id(self, admin_id: str) -> dict | None:
        # The id is the email, so this is the same lookup by another name.
        return self.get_by_email(admin_id)

    def list_all(self) -> list[dict]:
        rows = current_session().scalars(
            select(AdminRow).order_by(AdminRow.email)
        ).all()
        return [_to_dict(row) for row in rows]

    def create(self, email: str, full_name: str, hashed_password: bytes) -> dict:
        row = AdminRow(
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
admin_repository = AdminRepository()

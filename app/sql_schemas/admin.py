"""The `admins` table — isolated from `users` on purpose.

An admin is not a bank customer: no `AccountRow.owner_id` ever points here, and
`UserRow` never points here either. Two separate id spaces, two separate login
paths (`app/services/admin_service.py` vs `app/services/auth_service.py`),
so a bug in one cannot silently authenticate someone as the other.
"""

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.sql_schemas.tables import Base


class AdminRow(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

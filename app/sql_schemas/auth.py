from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.sql_schemas.tables import Base


class UserRow(Base):
    """A registered user, for the auth slice.

    Linked to `accounts` via `AccountRow.owner_id`, a foreign key back to here.
    """

    __tablename__ = "users"

    # The email, as `UserRepository.create()` has always set it. Keeping it means
    # the `id` field of every /auth response stays exactly what it was. Worth
    # revisiting if users are ever allowed to change their email, because then the
    # primary key changes with it — a surrogate UUID is the usual answer.

    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    # register_user() checks this in Python before inserting, which two
    # simultaneous registrations can both pass. The constraint is what actually
    # decides, and the repository turns the violation back into
    # EmailAlreadyRegisteredError.


    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # bcrypt hands back bytes and security.verify_password() expects bytes, so
    # store bytes. Encoding to text here would mean decoding on the way out and
    # getting it subtly wrong once.
    hashed_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

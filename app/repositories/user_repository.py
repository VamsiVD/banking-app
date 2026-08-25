import threading
from datetime import datetime, timezone

from app.errors import EmailAlreadyRegistered


class UserRepository:
    """In-memory stand-in for a real database. Only job: save/fetch user
    records. Swap this file's internals for real DB calls later without
    touching the service or controller."""

    def __init__(self):
        self._users_by_email: dict[str, dict] = {}
        # Guards the check-then-insert in create() — without it two concurrent
        # registrations for the same email can both pass the caller's
        # get_by_email() check and one silently overwrites the other.
        self._lock = threading.Lock()

    def get_by_email(self, email: str) -> dict | None:
        with self._lock:
            return self._users_by_email.get(email)

    def create(self, email: str, full_name: str, hashed_password: bytes) -> dict:
        with self._lock:
            if email in self._users_by_email:
                raise EmailAlreadyRegistered("email already registered")

            user = {
                "id": email,
                "email": email,
                "full_name": full_name,
                "hashed_password": hashed_password,
                "created_at": datetime.now(timezone.utc),
            }
            self._users_by_email[email] = user
            return user


# importer gets this same instance
user_repository = UserRepository()

import uuid
from datetime import datetime, timezone


class UserRepository:
    """In-memory stand-in for a real database. Only job: save/fetch user
    records. Swap this file's internals for real DB calls later without
    touching the service or controller."""

    def __init__(self):
        self._users_by_email: dict[str, dict] = {}

    def get_by_email(self, email: str) -> dict | None:
        return self._users_by_email.get(email)

    def get_by_id(self, user_id: str) -> dict | None:
        return next((u for u in self._users_by_email.values() if u["id"] == user_id), None)

    def create(self, email: str, full_name: str, hashed_password: bytes) -> dict:
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "created_at": datetime.now(timezone.utc),
        }
        self._users_by_email[email] = user
        return user



# importer gets this same instance
user_repository = UserRepository()

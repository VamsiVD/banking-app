from app.core import security
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    """Business rules for auth. No HTTP concerns (no status codes), no
    storage details (talks to the repo, not a dict), no crypto details
    (talks to app.core.security, not bcrypt directly)."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register_user(self, payload: RegisterRequest) -> dict:
        if self.repo.get_by_email(payload.email):
            raise EmailAlreadyRegisteredError("email already registered")

        hashed = security.hash_password(payload.password)
        return self.repo.create(payload.email, payload.full_name, hashed)

    def authenticate_user(self, payload: LoginRequest) -> dict:
        user = self.repo.get_by_email(payload.email)
        if user is None or not security.verify_password(payload.password, user["hashed_password"]):
            raise InvalidCredentialsError("incorrect email or password")

        return user

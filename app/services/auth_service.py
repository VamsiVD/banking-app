from app.core import security
from app.repositories.user_repository import user_repository
from app.schemas.auth_schema import LoginRequest, RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(payload: RegisterRequest) -> dict:
    if user_repository.get_by_email(payload.email):
        raise EmailAlreadyRegisteredError("email already registered")

    hashed = security.hash_password(payload.password)
    return user_repository.create(payload.email, payload.full_name, hashed)


def authenticate_user(payload: LoginRequest) -> dict:
    user = user_repository.get_by_email(payload.email)
    if user is None or not security.verify_password(payload.password, user["hashed_password"]):
        raise InvalidCredentialsError("incorrect email or password")

    return user
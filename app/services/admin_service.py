from app.core import security
from app.errors import AdminNotFound, EmailAlreadyRegistered, InvalidCredentials
from app.repositories.admin_repository import admin_repository
from app.api_schemas.auth_schema import LoginRequest, RegisterRequest


def register_admin(payload: RegisterRequest) -> dict:
    if admin_repository.get_by_email(payload.email):
        raise EmailAlreadyRegistered("email already registered")

    hashed = security.hash_password(payload.password)
    return admin_repository.create(payload.email, payload.full_name, hashed)


def authenticate_admin(payload: LoginRequest) -> dict:
    admin = admin_repository.get_by_email(payload.email)
    if admin is None or not security.verify_password(payload.password, admin["hashed_password"]):
        raise InvalidCredentials("incorrect email or password")

    return admin


def get_admin(admin_id: str) -> dict:
    admin = admin_repository.get_by_id(admin_id)
    if admin is None:
        raise AdminNotFound(f"No admin with id {admin_id!r}.")
    return admin


def list_admins() -> list[dict]:
    return admin_repository.list_all()

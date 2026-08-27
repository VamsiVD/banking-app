from fastapi import APIRouter, Depends, status

from app.api_schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserProfile,
)
from app.core import security
from app.core.auth_guard import get_current_admin
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_profile(admin: dict) -> UserProfile:
    # Also what keeps `hashed_password` off the wire: admin_service hands back
    # the whole record, and only these four fields leave here.
    return UserProfile(
        id=admin["id"],
        email=admin["email"],
        full_name=admin["full_name"],
        created_at=admin["created_at"],
    )


# Deliberately unguarded: guarding it means the first admin can never be created
# through the API at all. Fine for a training build, not for a real deployment —
# there, this becomes an admin-only route and the first record is seeded.
@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserProfile:
    return _to_profile(admin_service.register_admin(payload))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    admin = admin_service.authenticate_admin(payload)
    # The role claim is what separates this token from a customer's. Without it
    # the two are indistinguishable, since both subjects are email addresses.
    token = security.create_access_token(admin["id"], role=security.ROLE_ADMIN)

    return LoginResponse(access_token=token, token_type="bearer")


@router.get("/", response_model=list[UserProfile])
def list_admins(_admin=Depends(get_current_admin)) -> list[UserProfile]:
    return [_to_profile(admin) for admin in admin_service.list_admins()]


@router.get("/{admin_id}", response_model=UserProfile)
def get_admin(admin_id: str, _admin=Depends(get_current_admin)) -> UserProfile:
    return _to_profile(admin_service.get_admin(admin_id))

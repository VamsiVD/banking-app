from fastapi import APIRouter, status
from app.api_schemas.auth_schema import LoginRequest, RegisterRequest, UserProfile
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_profile(admin: dict) -> UserProfile:
    return UserProfile(
        id=admin["id"],
        email=admin["email"],
        full_name=admin["full_name"],
        created_at=admin["created_at"],
    )


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserProfile:
    return _to_profile(admin_service.register_admin(payload))


@router.post("/login", response_model=UserProfile)
def login(payload: LoginRequest) -> UserProfile:
    return _to_profile(admin_service.authenticate_admin(payload))


@router.get("/", response_model=list[UserProfile])
def list_admins() -> list[UserProfile]:
    return [_to_profile(admin) for admin in admin_service.list_admins()]


@router.get("/{admin_id}", response_model=UserProfile)
def get_admin(admin_id: str) -> UserProfile:
    return _to_profile(admin_service.get_admin(admin_id))

from fastapi import APIRouter, status

from app.core import security
from app.services import auth_service
from app.api_schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserProfile,
)
router = APIRouter(prefix="/auth", tags=["auth"])


def _to_profile(user: dict) -> UserProfile:
    return UserProfile(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"],
    )


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserProfile:
    return _to_profile(auth_service.register_user(payload))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = auth_service.authenticate_user(payload)
    token = security.create_access_token(user["id"])

    return LoginResponse(
        access_token=token,
        token_type="bearer",
    )


@router.get("/users", response_model=list[UserProfile])
def list_users() -> list[UserProfile]:
    return [_to_profile(user) for user in auth_service.list_users()]


@router.get("/users/{user_id}", response_model=UserProfile)
def get_user(user_id: str) -> UserProfile:
    return _to_profile(auth_service.get_user(user_id))

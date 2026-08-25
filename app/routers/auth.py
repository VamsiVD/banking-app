from fastapi import APIRouter, Depends, HTTPException, status
from app.repositories.user_repository import user_repository
from app.schemas.auth_schema import LoginRequest, RegisterRequest, UserProfile
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService(user_repository)


def _to_profile(user: dict) -> UserProfile:
    return UserProfile(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"],
    )


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserProfile:
    try:
        user = service.register_user(payload)
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    return _to_profile(user)


@router.post("/login", response_model=UserProfile)
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> UserProfile:
    try:
        user = service.authenticate_user(payload)
    except InvalidCredentialsError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))

    return _to_profile(user)

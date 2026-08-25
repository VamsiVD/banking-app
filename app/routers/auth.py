from fastapi import APIRouter, HTTPException, status
from app.schemas.auth_schema import LoginRequest, RegisterRequest, UserProfile
from app.services import auth_service
from app.services.auth_service import EmailAlreadyRegisteredError, InvalidCredentialsError

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
    try:
        user = auth_service.register_user(payload)
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    return _to_profile(user)


@router.post("/login", response_model=UserProfile)
def login(payload: LoginRequest) -> UserProfile:
    try:  
        user = auth_service.authenticate_user(payload)
    except InvalidCredentialsError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))

    return _to_profile(user)

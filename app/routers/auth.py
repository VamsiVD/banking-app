from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfile,
)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserProfile:
    # TODO: decode + verify JWT, load user, raise 401 on failure/expiry
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "get_current_user not implemented")


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserProfile:
    # TODO: check email not taken, bcrypt-hash password, persist user
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "register not implemented")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    # TODO: look up user by email, verify password hash, issue JWT
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "login not implemented")


@router.get("/me", response_model=UserProfile)
def read_current_user(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    return current_user

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


def _check_password_bytes(value: str) -> str:
    # bcrypt raises ValueError past 72 bytes; catch it here so an over-length
    # password comes back as a normal 422, not an unhandled 500 from hashpw.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must be at most 72 bytes when UTF-8 encoded")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255, description="user email, used as login id")
    password: str = Field(..., min_length=8, max_length=128, description="plain text password, hashed before storage")
    full_name: str = Field(..., min_length=1, max_length=100, description="user's full name")

    _validate_password = field_validator("password")(_check_password_bytes)


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255, description="user email, used as login id")
    password: str = Field(..., min_length=8, max_length=128, description="plain text password, checked against stored hash")

    _validate_password = field_validator("password")(_check_password_bytes)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="unique user id")
    email: EmailStr = Field(..., description="user email")
    full_name: str = Field(..., description="user's full name")
    created_at: datetime = Field(..., description="account creation timestamp")

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255, description="user email, used as login id")
    password: str = Field(..., min_length=8, max_length=128, description="plain text password, hashed before storage")
    full_name: str = Field(..., min_length=1, max_length=100, description="user's full name")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255, description="user email, used as login id")
    password: str = Field(..., min_length=8, max_length=128, description="plain text password, checked against stored hash")


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="unique user id")
    email: EmailStr = Field(..., description="user email")
    full_name: str = Field(..., description="user's full name")
    created_at: datetime = Field(..., description="account creation timestamp")

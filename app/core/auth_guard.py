from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.errors import InvalidToken
from app.repositories.user_repository import user_repository

# Read the Bearer token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# - Decode the access token
# - Get the user id/email from the token
# - Look up the user in the database
# - Raise 401 if token is invalid, expired, missing, or user does not exist
# - Return the current user if everything is valid

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Return the authenticated user for a valid Bearer token."""
    try:
        user_id = decode_access_token(token)
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_repository.get_by_email(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
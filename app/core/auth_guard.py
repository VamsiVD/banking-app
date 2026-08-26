from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Will read the Bearer token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# TODO:
# - Decode the access token
# - Get the user id/email from the token
# - Look up the user in the database
# - Raise 401 if token is invalid, expired, missing, or user does not exist
# - Return the current user if everything is valid
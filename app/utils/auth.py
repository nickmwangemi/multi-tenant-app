from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist
from fastapi import Header, HTTPException, status

from app.config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta  # Naive datetime
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(email: str, password: str):
    try:
        from app.models.core import CoreUser

        user = await CoreUser.get(email=email)
        return user if user.verify_password(password) else None
    except DoesNotExist:
        return None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def utc_now() -> datetime:
    """Return current UTC time as naive datetime"""
    return datetime.utcnow()


async def get_tenant_id(x_tenant: str = Header(...)):
    # Validate the tenant ID if necessary
    if not x_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-TENANT header is required"
        )
    return x_tenant

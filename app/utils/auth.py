from datetime import datetime, timedelta, timezone
from typing import Optional, Union, TYPE_CHECKING

from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist

from app.config import settings



SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if TYPE_CHECKING:
    from app.models.core import CoreUser
    from app.models.tenant import TenantUser

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(email: str, password: str, is_core: bool = True) -> Union["CoreUser", "TenantUser", None]:
    try:
        if is_core:
            from app.models.core import CoreUser  # Local import
            user = await CoreUser.get(email=email)
        else:
            user = await TenantUser.get(email=email)

        return None if not user or not user.verify_password(password) else user
    except DoesNotExist:
        return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def utc_now() -> datetime:
    """Return current UTC time as naive datetime"""
    return datetime.utcnow()
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from tortoise.exceptions import DoesNotExist

from app.config import settings
from app.models.core import CoreUser
from app.models.tenant import TenantUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    try:
        return (
            await CoreUser.get(id=user_id)
            if request.state.is_core
            else await TenantUser.get(id=user_id)
        )
    except DoesNotExist as exc:
        raise credentials_exception from exc

async def get_current_owner_user(current_user: CoreUser = Depends(get_current_user)):
    if not current_user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can perform this action",
        )
    return current_user




async def get_current_tenant_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    try:
        user = await TenantUser.get(email=email)
        if user is None:
            raise credentials_exception
        return user
    except DoesNotExist as exc:
        raise credentials_exception from exc
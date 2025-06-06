from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Header, HTTPException, status
from tortoise.exceptions import IntegrityError

from app.config import settings
from app.models.tenant import (TenantUser, TenantUser_Pydantic, TenantUserIn,
                               TenantUserIn_Pydantic)
from app.services.auth import get_current_tenant_user
from app.utils.auth import (authenticate_user, create_access_token,
                            get_password_hash, pwd_context)

router = APIRouter(prefix="/api", tags=["Tenant Operations (with X-TENANT header)"])

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


@router.post(
    "/auth/register",
    response_model=TenantUser_Pydantic,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant_user(user_data: TenantUserIn, x_tenant: str = Header(...)):
    if await TenantUser.exists(email=user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered in this tenant",
        )

    try:
        user_data.password_hash = get_password_hash(user_data.password)
        return await TenantUser.create(user_data.model_dump())
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed",
        ) from e


@router.post("/auth/login", response_model=dict)
async def login_tenant_user(
    email: str = Form(...), password: str = Form(...), x_tenant: str = Header(...)
):
    user = await authenticate_user(email, password, is_core=False)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=TenantUser_Pydantic)
async def get_current_user_profile(
    user: TenantUser = Depends(get_current_tenant_user), x_tenant: str = Header(...)
):
    return user


@router.put("/users/me", response_model=TenantUser_Pydantic)
async def update_current_user_profile(
    user_data: TenantUserIn_Pydantic,
    user: TenantUser = Depends(get_current_tenant_user),
    x_tenant: str = Header(...),
):
    user.email = user_data.email
    await user.save()
    return user

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from tortoise.exceptions import IntegrityError

from app.config import settings
from app.models.core import (
    AuthResponse,
    CoreUser,
    CoreUser_Pydantic,
    Organization,
    Token,
    UserLogin,
    UserRegisterIn,
)
from app.services.auth import get_current_user
from app.services.tenant import create_tenant_database, sync_owner_to_tenant
from app.utils.auth import authenticate_user, create_access_token

router = APIRouter(prefix="/api", tags=["Core Operations (no X-TENANT header)"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
VERIFICATION_TOKEN_EXPIRY_HOURS = settings.verification_token_expire_hours


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user_data: UserRegisterIn):
    if await CoreUser.exists(email=user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    try:
        import secrets

        verification_token = secrets.token_urlsafe(32)

        # Use naive datetime explicitly
        new_user = await CoreUser.create(
            email=user_data.email,
            password_hash=pwd_context.hash(user_data.password),
            is_owner=user_data.is_owner,
            verification_token=verification_token,
            verification_token_created_at=datetime.utcnow(),  # Naive datetime
        )

        access_token = create_access_token(
            data={"sub": str(new_user.id), "is_owner": new_user.is_owner},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        user_response = await CoreUser_Pydantic.from_tortoise_orm(new_user)
        return {
            "user": user_response,
            "access_token": access_token,
            "token_type": "bearer",
            "verification_token": verification_token,
        }

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed",
        ) from e


@router.get("/auth/verify")
async def verify_email(token: str):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is required",
        )

    user = await CoreUser.get_or_none(verification_token=token)
    if not user:
        raise HTTPException(
            status_code=404, detail="Invalid or expired verification token"
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    # Use naive datetime for comparison
    expiry_threshold = datetime.now(timezone.utc) - timedelta(
        hours=VERIFICATION_TOKEN_EXPIRY_HOURS
    )

    if user.verification_token_created_at < expiry_threshold:
        raise HTTPException(status_code=400, detail="Verification token has expired")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_created_at = None
    await user.save()

    return {"message": "Email verified successfully"}


@router.post("/reset-password")
async def request_password_reset(email: str):
    # Implementation here
    pass


@router.post("/auth/login", response_model=Token)
async def login_for_access_token(form_data: UserLogin):
    user = await authenticate_user(form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "is_owner": user.is_owner},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/organizations")
async def create_organization(name: str, user: CoreUser = Depends(get_current_user)):
    if not user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create organizations",
        )

    organization = await Organization.create(name=name, owner=user)
    tenant_db_name = await create_tenant_database(organization.id)
    await sync_owner_to_tenant(organization.id, user.id)

    return {
        "organization_id": organization.id,
        "tenant_db_name": tenant_db_name,
        "message": "Organization created successfully",
    }

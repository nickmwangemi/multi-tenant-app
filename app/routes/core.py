from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from tortoise.exceptions import IntegrityError

from app.models.core import CoreUser, CoreUser_Pydantic, UserRegisterIn
from app.services.auth import get_current_user
from app.utils.auth import create_access_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post(
    "/auth/register",
    response_model=CoreUser_Pydantic,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user_data: UserRegisterIn):
    if await CoreUser.exists(email=user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    try:
        new_user = await CoreUser.create(
            email=user_data.email,
            password_hash=pwd_context.hash(user_data.password),
            is_owner=user_data.is_owner,  # Set owner status
        )
        return await CoreUser_Pydantic.from_tortoise_orm(new_user)
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed",
        ) from e


@router.get("/auth/verify")
async def verify_email(token: str):
    user = await CoreUser.get_or_none(verification_token=token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    user.is_verified = True
    user.verification_token = None
    await user.save()

    return {"message": "Email verified successfully"}


@router.post("/auth/reset-password")
async def request_password_reset(email: str):
    # Implementation here
    pass


@router.post("/auth/login")
async def login(credentials: UserRegisterIn):
    user = await CoreUser.get_or_none(email=credentials.email)
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    # Generate JWT token
    return {"access_token": create_access_token(user.id)}


@router.post("/organizations")
async def create_organization(user: CoreUser_Pydantic = Depends(get_current_user)):
    # Implement organization creation logic
    # if not current_user.is_owner:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only owners can create organizations"
    #     )
    pass

from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, constr
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model

from app.utils.auth import pwd_context, utc_now


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserRegisterIn(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    is_owner: bool = False


class CoreUser(Model):
    __tablename__ = "core_users"

    id = fields.IntField(pk=True)
    email = fields.CharField(255, unique=True)
    password_hash = fields.CharField(128)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_verified = fields.BooleanField(default=False)
    is_owner = fields.BooleanField(default=False)
    verification_token = fields.CharField(max_length=255, null=True)
    verification_token_created_at = fields.DatetimeField(null=True)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password_hash)

    def __str__(self):
        return self.email


CoreUser_Pydantic = pydantic_model_creator(
    CoreUser, name="CoreUser", exclude=("password_hash",)
)

CoreUserIn_Pydantic = pydantic_model_creator(
    CoreUser, name="CoreUserIn", exclude_readonly=True, exclude=("is_verified",)
)


class AuthResponse(BaseModel):
    user: CoreUser_Pydantic
    access_token: str
    token_type: str
    verification_token: str

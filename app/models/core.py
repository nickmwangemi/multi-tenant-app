from datetime import datetime

from pydantic import BaseModel, EmailStr, constr
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


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
    id = fields.IntField(pk=True)
    email = fields.CharField(255, unique=True)
    password_hash = fields.CharField(128)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_verified = fields.BooleanField(default=False)
    is_owner = fields.BooleanField(default=False)
    verification_token = fields.CharField(max_length=255, null=True)
    verification_token_created_at = fields.DatetimeField(null=True)

    def verify_password(self, plain_password: str) -> bool:
        from app.utils.auth import pwd_context

        return pwd_context.verify(plain_password, self.password_hash)

    def __str__(self):
        return self.email

    @classmethod
    async def create_user(cls, **kwargs):
        """Helper method to ensure proper datetime handling"""
        if "verification_token_created_at" not in kwargs:
            kwargs["verification_token_created_at"] = datetime.utcnow()
        return await cls.create(**kwargs)


class Organization(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)
    owner = fields.ForeignKeyField("models.CoreUser", related_name="organizations")
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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

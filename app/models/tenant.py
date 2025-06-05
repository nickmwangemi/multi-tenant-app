from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel, EmailStr, constr

class TenantUserIn(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

class TenantUser(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(255, unique=True)
    password_hash = fields.CharField(128)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)

    def verify_password(self, plain_password: str) -> bool:
        from app.utils.auth import pwd_context
        return pwd_context.verify(plain_password, self.password_hash)

    def __str__(self):
        return self.email

TenantUser_Pydantic = pydantic_model_creator(
    TenantUser, name="TenantUser", exclude=("password_hash",)
)
TenantUserIn_Pydantic = pydantic_model_creator(
    TenantUser, name="TenantUserIn", exclude_readonly=True, exclude=("is_active",)
)

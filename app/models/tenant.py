from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class TenantUser(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(50, unique=True)
    password_hash = fields.CharField(128)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.username


TenantUser_Pydantic = pydantic_model_creator(TenantUser, name="TenantUser")
TenantUserIn_Pydantic = pydantic_model_creator(
    TenantUser, name="TenantUserIn", exclude_readonly=True
)

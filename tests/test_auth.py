import uuid
import pytest
from datetime import timedelta
from jose import jwt
from app.config import settings
from app.models.tenant import TenantUser
from app.utils.auth import authenticate_user, create_access_token, get_password_hash
from tortoise import Tortoise

@pytest.mark.asyncio
async def test_authenticate_core_user_success():
    from app.models.core import CoreUser
    from app.utils.password import get_password_hash

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_user = await CoreUser.create(
        email=test_email,
        password_hash=get_password_hash("secret"),
        is_verified=True
    )

    try:
        user = await authenticate_user(test_email, "secret")
        assert user is not None
        assert user.email == test_email
    finally:
        await test_user.delete()

@pytest.mark.asyncio
async def test_authenticate_core_user_wrong_password(core_user):
    user = await authenticate_user(core_user.email, "wrongpassword")
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_core_user_not_found():
    user = await authenticate_user("nonexistent@example.com", "secret")
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_core_user_success(core_user):
    user = await authenticate_user(core_user.email, "secret")
    assert user is not None
    assert user.email == core_user.email

def test_create_access_token():
    token = create_access_token({"sub": "123"})
    assert isinstance(token, str)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "123"

def test_token_expiry():
    token = create_access_token({"sub": "123"}, expires_delta=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

@pytest.fixture
async def tenant_user(init_tenant_db):
    user = await TenantUser.create(
        email="tenant@example.com",
        password_hash=get_password_hash("secret"),
        is_active=True
    )
    yield user
    await user.delete()

@pytest.mark.asyncio
async def test_authenticate_tenant_user_success(tenant_user):
    user = await authenticate_user(tenant_user.email, "secret", is_core=False)
    assert user is not None
    assert user.email == tenant_user.email

@pytest.mark.asyncio
async def test_authenticate_tenant_user_inactive(tenant_user):
    tenant_user.is_active = False
    await tenant_user.save()

    user = await authenticate_user(tenant_user.email, "secret", is_core=False)
    assert user is None

import uuid

import pytest
from datetime import timedelta
from jose import jwt

from app.config import settings
from app.models.tenant import TenantUser
from app.utils.auth import authenticate_user, create_access_token

from tortoise import Tortoise


@pytest.mark.asyncio
async def test_authenticate_core_user_success():
    # Create a unique test user
    from app.models.core import CoreUser
    from app.utils.password import get_password_hash

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_user = await CoreUser.create(
        email=test_email,
        password_hash=get_password_hash("secret"),
        is_verified=True
    )

    try:
        # Test authentication
        user = await authenticate_user(test_email, "secret")
        assert user is not None
        assert user.email == test_email
    finally:
        # Clean up
        await test_user.delete()

@pytest.mark.asyncio
async def test_authenticate_core_user_wrong_password(core_user):
    user = await authenticate_user("test@example.com", "wrongpassword")
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_core_user_not_found():
    user = await authenticate_user("nonexistent@example.com", "secret")
    assert user is None


@pytest.mark.asyncio
async def test_authenticate_tenant_user_success(tenant_user):
    # First verify the test user exists directly in database
    from app.models.tenant import TenantUser

    # Get user directly from database
    existing_user = await TenantUser.filter(email="tenant@example.com").first()
    assert existing_user is not None, "Test user not found in database"

    # Test authentication
    user = await authenticate_user(
        email="tenant@example.com",
        password="secret",  # Must match the hashed password in fixture
        is_core=False
    )

    assert user is not None, "Authentication failed"
    assert user.email == "tenant@example.com"


@pytest.mark.asyncio
async def test_authenticate_tenant_user_inactive(tenant_user):
    # Ensure user is initially active
    assert tenant_user.is_active is True

    # Deactivate user
    tenant_user.is_active = False
    await tenant_user.save()

    # Verify the change was saved
    refreshed_user = await TenantUser.get(id=tenant_user.id)
    assert refreshed_user.is_active is False

    # Test authentication
    user = await authenticate_user(tenant_user.email, "secret", is_core=False)

    # Should return None for inactive users
    assert user is None, "Inactive user should not authenticate"

def test_create_access_token():
    token = create_access_token({"sub": "123"})
    assert isinstance(token, str)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "123"

def test_token_expiry():
    token = create_access_token({"sub": "123"}, expires_delta=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
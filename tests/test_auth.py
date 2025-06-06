import pytest
from fastapi import HTTPException
from passlib.context import CryptContext

from app.models.core import CoreUser
from app.models.tenant import TenantUser
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    verify_password,
    get_password_hash,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_core_user():
    hashed_password = get_password_hash("testpassword")
    user = await CoreUser.create(
        email="test@example.com",
        password_hash=hashed_password,
        is_verified=True,
        is_owner=False,
    )
    yield user
    await user.delete()


@pytest.fixture
async def test_tenant_user():
    hashed_password = get_password_hash("testpassword")
    user = await TenantUser.create(
        email="tenant@example.com",
        password_hash=hashed_password,
        is_active=True,
    )
    yield user
    await user.delete()


class TestAuthenticateUser:
    async def test_authenticate_core_user_success(self, test_core_user):
        user = await authenticate_user("test@example.com", "testpassword")
        assert user is not None
        assert user.email == "test@example.com"
        assert isinstance(user, CoreUser)

    async def test_authenticate_core_user_wrong_password(self, test_core_user):
        user = await authenticate_user("test@example.com", "wrongpassword")
        assert user is None

    async def test_authenticate_core_user_not_found(self):
        user = await authenticate_user("nonexistent@example.com", "testpassword")
        assert user is None

    async def test_authenticate_tenant_user_success(self, test_tenant_user):
        user = await authenticate_user(
            "tenant@example.com", "testpassword", is_core=False
        )
        assert user is not None
        assert user.email == "tenant@example.com"
        assert isinstance(user, TenantUser)

    async def test_authenticate_tenant_user_wrong_password(self, test_tenant_user):
        user = await authenticate_user(
            "tenant@example.com", "wrongpassword", is_core=False
        )
        assert user is None

    async def test_authenticate_tenant_user_not_found(self):
        user = await authenticate_user(
            "nonexistent@example.com", "testpassword", is_core=False
        )
        assert user is None


class TestPasswordHashing:
    def test_password_hashing(self):
        password = "testpassword"
        hashed_password = get_password_hash(password)
        assert verify_password(password, hashed_password)
        assert not verify_password("wrongpassword", hashed_password)


class TestJWTToken:
    def test_create_access_token(self):
        token = create_access_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        from datetime import timedelta

        token = create_access_token({"sub": "123"}, expires_delta=timedelta(minutes=5))
        assert isinstance(token, str)
        assert len(token) > 0

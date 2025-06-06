import pytest
from datetime import timedelta, datetime
from jose import jwt
from fastapi import HTTPException, status

from app.config import settings
from app.utils.auth import (
    authenticate_user,
    create_access_token
)

@pytest.mark.asyncio
class TestAuthentication:
    async def test_authenticate_core_user_success(self, core_user):
        user = await authenticate_user("test@example.com", "secret")
        assert user is not None
        assert user.email == "test@example.com"

    async def test_authenticate_core_user_wrong_password(self, core_user):
        user = await authenticate_user("test@example.com", "wrongpassword")
        assert user is None

    async def test_authenticate_core_user_not_found(self):
        user = await authenticate_user("nonexistent@example.com", "secret")
        assert user is None

    async def test_authenticate_tenant_user_success(self, tenant_user):
        user = await authenticate_user("tenant@example.com", "secret", is_core=False)
        assert user is not None
        assert user.email == "tenant@example.com"

    async def test_authenticate_tenant_user_inactive(self, tenant_user):
        tenant_user.is_active = False
        await tenant_user.save()
        user = await authenticate_user("tenant@example.com", "secret", is_core=False)
        assert user is None

    def test_create_access_token(self):
        token = create_access_token({"sub": "123"})
        assert isinstance(token, str)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "123"

    def test_token_expiry(self):
        token = create_access_token({"sub": "123"}, expires_delta=timedelta(minutes=-1))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        with pytest.raises(HTTPException) as exc_info:
            if payload["exp"] < datetime.utcnow().timestamp():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )
        assert exc_info.value.status_code == 401
import uuid

import pytest
from tortoise import Tortoise

from app.config import settings
from app.db.routing import TenantRouter
from app.middleware.tenant_context import current_tenant
from app.models.core import CoreUser
from app.models.tenant import TenantUser

@pytest.mark.asyncio
async def test_core_db_routing(test_client, core_user):
    # Should use core database
    response = await test_client.post(
        "/api/auth/register",
        json={
            "email": "routing@core.com",
            "password": "RoutingPass123!",
            "is_owner": True,
        },
    )
    assert response.status_code == 201

    # Verify in core database
    user = await CoreUser.get(email="routing@core.com")
    assert user is not None


@pytest.mark.asyncio
async def test_tenant_db_routing(test_client, tenant_db):
    # Add proper event loop handling
    import asyncio
    loop = asyncio.get_event_loop()

    # Generate unique test data
    test_email = f"test_{uuid.uuid4().hex[:8]}@tenant.com"

    # Initialize Tortoise with proper loop
    await Tortoise.init(
        db_url=f"postgres://test_user:test_password@localhost:5432/test_tenant_{tenant_db}",
        modules={"models": ["app.models.tenant"]},
        _create_db=False
    )

    try:
        # Test registration
        response = await test_client.post(
            "/api/auth/register",
            json={"email": test_email, "password": "ValidPass123!"},
            headers={"X-TENANT": str(tenant_db)}
        )
        assert response.status_code == 201

        # Verify in tenant database
        user = await TenantUser.get(email=test_email)
        assert user is not None
    finally:
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_tenant_router():
    router = TenantRouter()

    # Test with tenant context
    current_tenant.set(1)
    assert await router.db_for_read(None) is not None
    assert await router.db_for_write(None) is not None

    # Test without tenant context
    current_tenant.set(None)
    assert await router.db_for_read(None) == "default"
    assert await router.db_for_write(None) == "default"
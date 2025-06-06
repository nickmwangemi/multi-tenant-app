import pytest
from tortoise import connections
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
    # Should use tenant database
    response = await test_client.post(
        "/api/auth/register",
        json={"email": "routing@tenant.com", "password": "RoutingPass123!"},
        headers={"X-TENANT": str(tenant_db)},
    )
    assert response.status_code == 201

    # Verify in tenant database
    user = await TenantUser.get(email="routing@tenant.com")
    assert user is not None

    # Verify NOT in core database
    assert not await CoreUser.exists(email="routing@tenant.com")
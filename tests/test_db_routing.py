import pytest
from tortoise import connections


@pytest.mark.asyncio
async def test_core_db_routing(client):
    # Should use core database
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "routing@core.com",
            "password": "RoutingPass123!",
            "is_owner": True,
            "name": "Test User",
        },
    )
    assert response.status_code == 201

    # Verify in core database
    conn = connections.get("default")
    user = await conn.execute_query_dict(
        "SELECT * FROM coreuser WHERE email = 'routing@core.com'"
    )
    assert len(user) > 0


@pytest.mark.asyncio
async def test_tenant_db_routing(client, tenant_db):
    # Should use tenant database
    response = await client.post(
        "/api/auth/register",
        json={"email": "routing@tenant.com", "password": "RoutingPass123!"},
        headers={"X-TENANT": str(tenant_db)},
    )
    assert response.status_code == 201

    # Verify in tenant database
    tenant_conn = await connections.get(f"tenant_{tenant_db}")
    user = await tenant_conn.execute_query_dict(
        "SELECT * FROM tenantuser WHERE email = 'routing@tenant.com'"
    )
    assert len(user) > 0

    # Verify NOT in core database
    core_conn = connections.get("default")
    core_user = await core_conn.execute_query_dict(
        "SELECT * FROM coreuser WHERE email = 'routing@tenant.com'"
    )
    assert len(core_user) == 0

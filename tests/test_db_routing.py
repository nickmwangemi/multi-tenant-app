import pytest
from tortoise import Tortoise

from app.config import settings
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
    # Generate unique test data
    import uuid
    test_email = f"routing_{uuid.uuid4().hex[:8]}@tenant.com"
    test_password = "ValidPass123!"

    # Register tenant user
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": test_email,
            "password": test_password
        },
        headers={"X-TENANT": str(tenant_db)},
    )

    # Debug output if failed
    if response.status_code != 201:
        print(f"Registration failed. Status: {response.status_code}, Response: {response.json()}")

    assert response.status_code == 201, \
        f"Expected 201 Created, got {response.status_code}. Response: {response.json()}"

    # Verify in tenant database
    await Tortoise.init({
        "connections": {
            "tenant": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "database": f"test_tenant_{tenant_db}",
                    "host": "localhost",
                    "password": "postgres",
                    "port": 5432,
                    "user": "postgres"
                }
            }
        },
        "apps": {
            "tenant": {
                "models": ["app.models.tenant"],
                "default_connection": "tenant",
            }
        },
    })

    try:
        user = await TenantUser.get(email=test_email)
        assert user is not None, f"User {test_email} not found in tenant database"
        assert await user.verify_password(test_password), "Password verification failed"
    finally:
        await Tortoise.close_connections()


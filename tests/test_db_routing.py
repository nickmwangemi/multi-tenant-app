import asyncio
import uuid

import pytest
from tortoise import Tortoise

from app.config import settings
from app.db.routing import TenantRouter, get_tenant_connection
from app.middleware.tenant_context import current_tenant
from app.models.core import CoreUser
from app.models.tenant import TenantUser


async def test_core_db_routing(test_client):
    unique_email = f"test_{uuid.uuid4().hex}@example.com"
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "ValidPass123!",
            "is_owner": True,
        },
    )
    assert (
        response.status_code == 201
    ), f"Expected 201, got {response.status_code}. Response: {response.json()}"


@pytest.mark.asyncio
async def test_tenant_db_routing(test_client, init_tenant_db, tenant_db):
    test_email = f"test_{uuid.uuid4().hex[:8]}@tenant.com"

    response = await test_client.post(
        "/api/auth/register",
        json={"email": test_email, "password": "ValidPass123!"},
        headers={"X-TENANT": str(tenant_db)},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_tenant_router():
    router = TenantRouter()

    current_tenant.set(1)
    assert await router.db_for_read(None) is not None
    assert await router.db_for_write(None) is not None

    current_tenant.set(None)
    assert await router.db_for_read(None) == "default"
    assert await router.db_for_write(None) == "default"


@pytest.mark.asyncio
async def test_get_tenant_connection():
    tenant_id = 1
    conn = await get_tenant_connection(tenant_id)
    assert conn is not None
    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_get_tenant_connection_existing():
    tenant_id = 1
    # First call creates connection
    await get_tenant_connection(tenant_id)
    # Second call should reuse existing
    conn = await get_tenant_connection(tenant_id)
    assert conn is not None
    await Tortoise.close_connections()

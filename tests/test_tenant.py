import pytest
import asyncpg

from app.config import settings
from app.models.core import Organization
from app.services.tenant import create_tenant_database

@pytest.fixture
async def setup_tenant(core_user):
    # Use admin connection for setup
    admin_conn = await asyncpg.connect(
        host="localhost",
        user="postgres",
        password="postgres"
    )
    try:
        org = await Organization.create(name="Test Tenant", owner=core_user)
        db_name = f"tenant_{org.id}"
        await admin_conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')
        yield org.id
    finally:
        await admin_conn.close()

@pytest.mark.asyncio
async def test_register_tenant_user(test_client, setup_tenant):
    tenant_id = await setup_tenant
    response = test_client.post(
        "/api/auth/register",
        headers={"X-TENANT": str(tenant_id)},
        json={"email": "tenant_user@test.com", "password": "TenantPass123!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "tenant_user@test.com"

@pytest.mark.asyncio
async def test_tenant_login(test_client, setup_tenant):
    tenant_id = await setup_tenant

    # Register user first
    test_client.post(
        "/api/auth/register",
        headers={"X-TENANT": str(tenant_id)},
        json={"email": "login@tenant.com", "password": "LoginPass123!"},
    )

    response = test_client.post(
        "/api/auth/login",
        headers={"X-TENANT": str(tenant_id)},
        data={"email": "login@tenant.com", "password": "LoginPass123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
import pytest
import asyncpg
from app.config import settings
from app.models.core import Organization
from app.services.tenant import create_tenant_database
from tortoise import Tortoise

@pytest.fixture
async def setup_tenant(core_user):
    org = await Organization.create(name="Test Tenant", owner=core_user)

    conn = await asyncpg.connect(
        "postgres://test_user:test_password@localhost:5432/test_core"
    )
    try:
        db_name = f"tenant_{org.id}"
        await conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')

        tenant_conn = await asyncpg.connect(
            f"postgres://test_user:test_password@localhost:5432/{db_name}"
        )
        await tenant_conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await tenant_conn.close()

        await Tortoise.init(
            db_url=f"postgres://test_user:test_password@localhost:5432/{db_name}",
            modules={"models": ["app.models.tenant", "aerich.models"]},
            _create_db=False
        )
        await Tortoise.generate_schemas()

        yield org.id
    finally:
        await Tortoise.close_connections()
        await conn.close()

        admin_conn = await asyncpg.connect(
            "postgres://postgres:postgres@localhost:5432/postgres"
        )
        try:
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        finally:
            await admin_conn.close()

@pytest.mark.asyncio
async def test_register_tenant_user(test_client, setup_tenant):
    tenant_id = await setup_tenant
    response = await test_client.post(
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

    await test_client.post(
        "/api/auth/register",
        headers={"X-TENANT": str(tenant_id)},
        json={"email": "login@tenant.com", "password": "LoginPass123!"},
    )

    response = await test_client.post(
        "/api/auth/login",
        headers={"X-TENANT": str(tenant_id)},
        data={"username": "login@tenant.com", "password": "LoginPass123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

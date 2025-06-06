import pytest
import asyncpg
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.models.core import CoreUser, Organization
from app.services.tenant import create_tenant_database

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
async def setup_tenant():
    # Create core objects
    owner = await CoreUser.create(
        email="tenant_owner@test.com",
        password_hash="hashed_password",
        is_owner=True,
        is_verified=True,
    )
    org = await Organization.create(name="Test Tenant", owner=owner)

    # Create tenant database
    await create_tenant_database(org.id)
    yield
    # Cleanup
    conn = await asyncpg.connect(settings.database_url)
    await conn.execute(f'DROP DATABASE IF EXISTS "tenant_{org.id}"')
    await conn.close()


@pytest.mark.asyncio
async def test_register_tenant_user():
    response = client.post(
        "/api/auth/register",
        headers={"X-TENANT": "1"},
        json={"email": "tenant_user@test.com", "password": "TenantPass123!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "tenant_user@test.com"


@pytest.mark.asyncio
async def test_tenant_login():
    # Register user first
    client.post(
        "/api/auth/register",
        headers={"X-TENANT": "1"},
        json={"email": "login@tenant.com", "password": "LoginPass123!"},
    )

    response = client.post(
        "/api/auth/login",
        headers={"X-TENANT": "1"},
        data={"email": "login@tenant.com", "password": "LoginPass123!"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

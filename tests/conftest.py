import uuid

import pytest
from httpx import AsyncClient
from tortoise import Tortoise

from app.config import settings
from app.main import app
from app.models.core import CoreUser
from app.models.tenant import TenantUser

# Override database settings for tests
settings.database_url = "postgres://test:test@localhost:5432/test_core"
settings.tenant_database_base = "postgres://test:test@localhost:5432"


@pytest.fixture(scope="session")
async def initialize_db():
    await Tortoise.init(
        db_url="postgres://test:test@localhost:5432/test",
        modules={"models": ["app.models.core"]},
        _create_db=True,
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
    await Tortoise._drop_databases()


@pytest.fixture
async def client():
    async with AsyncClient(base_url="http://localhost:8000") as ac:
        yield ac


@pytest.fixture
async def owner_token(client):
    email = f"owner-{uuid.uuid4()}@test.com"

    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "securepass123", "is_owner": True},
    )
    return response.json()["access_token"]


@pytest.fixture
async def tenant_db(client, owner_token):
    response = await client.post(
        "/api/organizations",
        json={"name": "TestOrg"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert (
        response.status_code == 201
    ), f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert "organization_id" in data, f"Missing 'organization_id' in response: {data}"
    return data["organization_id"]


@pytest.fixture(autouse=True)
async def clean_db():
    yield
    # Clean database after each test
    for model in [CoreUser, TenantUser]:
        await model.all().delete()

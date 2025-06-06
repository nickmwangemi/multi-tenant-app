import pytest
import asyncpg
import contextlib
from tortoise import Tortoise, run_async
from tortoise.contrib.test import initializer

from app.config import settings
from app.models.core import CoreUser
from app.models.tenant import TenantUser

# Override settings for tests
settings.database_url = "postgres://postgres:postgres@localhost:5432/test_core"
settings.tenant_database_base = "postgres://postgres:postgres@localhost:5432"

@pytest.fixture(scope="session", autouse=True)
def initialize_db():
    # Initialize core database
    initializer(
        ["app.models.core", "app.models.tenant", "aerich.models"],
        db_url=settings.database_url,
        app_label="models",
    )

    # Create test tenant databases
    async def create_test_tenant():
        conn = await asyncpg.connect(settings.database_url)
        for i in range(1, 3):  # Create 2 test tenant databases
            db_name = f"test_tenant_{i}"
            with contextlib.suppress(asyncpg.DuplicateDatabaseError):
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        await conn.close()

    run_async(create_test_tenant())

    yield

    # Cleanup
    run_async(Tortoise.close_connections())

    async def cleanup_tenant_dbs():
        conn = await asyncpg.connect(settings.database_url)
        for i in range(1, 3):
            db_name = f"test_tenant_{i}"
            with contextlib.suppress(asyncpg.PostgresError):
                await conn.execute(f'DROP DATABASE "{db_name}"')
        await conn.close()

    run_async(cleanup_tenant_dbs())

@pytest.fixture
async def test_client():
    from fastapi.testclient import TestClient
    from app.main import app

    # Initialize Tortoise for the app
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["app.models.core", "app.models.tenant"]},
    )
    await Tortoise.generate_schemas()

    with TestClient(app) as client:
        yield client

    await Tortoise.close_connections()

@pytest.fixture
async def core_user():
    user = await CoreUser.create(
        email="test@example.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPVgaYl5O",  # "secret"
        is_verified=True
    )
    yield user
    await user.delete()

@pytest.fixture
async def tenant_user():
    # Initialize tenant database connection
    await Tortoise.init(
        {
            "connections": {
                "test_tenant_1": f"{settings.tenant_database_base}/test_tenant_1"
            },
            "apps": {
                "tenant": {
                    "models": ["app.models.tenant"],
                    "default_connection": "test_tenant_1",
                }
            },
        }
    )
    await Tortoise.generate_schemas()

    user = await TenantUser.create(
        email="tenant@example.com",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPVgaYl5O",
        is_active=True
    )
    yield user
    await user.delete()
    await Tortoise.close_connections()

@pytest.fixture
async def tenant_db():
    return 1  # Return first test tenant ID
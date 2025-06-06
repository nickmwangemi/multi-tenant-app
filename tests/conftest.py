import uuid

import pytest
import asyncpg
import asyncio
import contextlib
from tortoise import Tortoise

from app.config import settings
from app.models.core import CoreUser
from app.models.tenant import TenantUser

# Override settings for tests
settings.database_url = "postgres://postgres:postgres@localhost:5432/test_core"
settings.tenant_database_base = "postgres://postgres:postgres@localhost:5432"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def initialize_db():
    # Initialize core database
    await Tortoise.init(
        db_url=settings.database_url,
        modules={
            "models": ["app.models.core", "app.models.tenant", "aerich.models"],
            "tenant": ["app.models.tenant"]
        }
    )
    await Tortoise.generate_schemas()

    # Create test tenant databases
    conn = await asyncpg.connect(settings.database_url)
    for i in range(1, 3):
        db_name = f"test_tenant_{i}"
        with contextlib.suppress(asyncpg.DuplicateDatabaseError):
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    await conn.close()

    yield

    # Cleanup
    await Tortoise.close_connections()
    conn = await asyncpg.connect(settings.database_url)
    for i in range(1, 3):
        db_name = f"test_tenant_{i}"
        with contextlib.suppress(asyncpg.PostgresError):
            await conn.execute(f'DROP DATABASE "{db_name}"')
    await conn.close()

@pytest.fixture
async def test_client():
    from fastapi.testclient import TestClient
    from app.main import app

    # Initialize Tortoise for FastAPI app
    await Tortoise.init(
        db_url=settings.database_url,
        modules={
            "models": ["app.models.core", "app.models.tenant", "aerich.models"],
            "tenant": ["app.models.tenant"]
        }
    )

    with TestClient(app) as client:
        yield client

    await Tortoise.close_connections()


@pytest.fixture
async def core_user():
    from app.utils.password import get_password_hash
    from app.models.core import CoreUser

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await CoreUser.create(
        email=test_email,
        password_hash=get_password_hash("secret"),
        is_verified=True
    )
    yield user
    await user.delete()


@pytest.fixture
async def tenant_user():
    from app.utils.password import get_password_hash

    # Initialize tenant database connection
    await Tortoise.init({
        "connections": {
            "tenant": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "database": "test_tenant_1",
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
    await Tortoise.generate_schemas()

    # Create user with properly hashed password
    user = await TenantUser.create(
        email="tenant@example.com",
        password_hash=get_password_hash("secret"),  # Hash matches test password
        is_active=True
    )

    yield user

    # Cleanup
    await user.delete()
    await Tortoise.close_connections()

@pytest.fixture
async def tenant_db():
    return 1  # Return first test tenant ID


@pytest.fixture(autouse=True)
async def clean_db():
    """Clean database between tests."""
    yield
    # Clean core database
    conn = await Tortoise.get_connection("default")
    await conn.execute_query("DELETE FROM coreuser")
    await conn.execute_query("DELETE FROM organization")

    	# Clean tenant databases
    for i in range(1, 3):
        with contextlib.suppress(KeyError):
            tenant_conn = await Tortoise.get_connection(f"tenant_{i}")
            await tenant_conn.execute_query("DELETE FROM tenantuser")
import asyncio
import contextlib
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.config import settings
from app.models.core import CoreUser


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def initialize_db():
    admin_conn = await asyncpg.connect(
        "postgres://postgres:postgres@localhost:5432/postgres"
    )

    try:
        # Create databases if they don't exist
        for db in ["test_core", "test_tenant_1", "test_tenant_2"]:
            exists = await admin_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db
            )
            if not exists:
                await admin_conn.execute(f'CREATE DATABASE "{db}" OWNER test_user')

        # Initialize core schema
        await Tortoise.init(
            db_url="postgres://test_user:test_password@localhost:5432/test_core",
            modules={"models": ["app.models.core", "aerich.models"]},
            _create_db=False,
        )
        await Tortoise.generate_schemas()

        yield

        # Cleanup
        await Tortoise.close_connections()
    finally:
        await admin_conn.close()


@pytest.fixture
async def test_client():
    from app.main import app

    # Reinitialize connections
    await Tortoise.init(
        db_url="postgres://test_user:test_password@localhost:5432/test_core",
        modules={"models": ["app.models.core", "app.models.tenant", "aerich.models"]},
        _create_db=False,
    )

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def core_user():
    # Initialize database first
    await Tortoise.init(
        db_url="postgres://test_user:test_password@localhost:5432/test_core",
        modules={"models": ["app.models.core", "aerich.models"]},
        _create_db=False,
    )
    await Tortoise.generate_schemas()

    from app.utils.auth import get_password_hash

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await CoreUser.create(
        email=test_email, password_hash=get_password_hash("secret"), is_verified=True
    )
    yield user
    await user.delete()
    await Tortoise.close_connections()


@pytest.fixture
async def unverified_core_user():
    # Initialize database first
    await Tortoise.init(
        db_url="postgres://test_user:test_password@localhost:5432/test_core",
        modules={"models": ["app.models.core", "aerich.models"]},
        _create_db=False,
    )
    await Tortoise.generate_schemas()

    from app.utils.auth import get_password_hash

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await CoreUser.create(
        email=test_email, password_hash=get_password_hash("secret"), is_verified=False
    )
    yield user
    await user.delete()
    await Tortoise.close_connections()


@pytest.fixture
async def tenant_db():
    return 1  # Return first test tenant ID


@pytest.fixture
async def init_tenant_db(tenant_db):
    db_name = f"test_tenant_{tenant_db}"
    await Tortoise.init(
        db_url=f"postgres://test_user:test_password@localhost:5432/{db_name}",
        modules={"models": ["app.models.tenant"]},
        _create_db=False,
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def cleanup_db():
    """Clean up connections after each test"""
    yield
    await Tortoise.close_connections()

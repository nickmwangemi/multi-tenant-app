import uuid

import pytest
import asyncpg
import asyncio
from tortoise import Tortoise
from app.config import settings
from app.models.core import CoreUser


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def initialize_db():
    # Create admin connection
    admin_conn = await asyncpg.connect(
        host="localhost",
        user="postgres",
        password="postgres"
    )

    try:
        # Create test user with permissions
        await admin_conn.execute("""
            CREATE USER test_user WITH PASSWORD 'test_password';
            GRANT ALL PRIVILEGES ON DATABASE test_core TO test_user;
            ALTER USER test_user CREATEDB;
        """)

        # Initialize core database with test user
        await Tortoise.init(
            db_url="postgres://test_user:test_password@localhost:5432/test_core",
            modules={"models": ["app.models.core", "app.models.tenant", "aerich.models"]}
        )
        await Tortoise.generate_schemas()

        # Create test tenant databases
        for i in range(1, 3):
            db_name = f"test_tenant_{i}"
            await admin_conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')
    finally:
        await admin_conn.close()

@pytest.fixture
async def test_client():
    from fastapi.testclient import TestClient
    from app.main import app

    # Initialize Tortoise for FastAPI app
    await Tortoise.init(
        db_url=settings.database_url,
        modules={
            "models": ["app.models.core", "app.models.tenant", "aerich.models"],
        }
    )

    with TestClient(app) as client:
        yield client

    await Tortoise.close_connections()

@pytest.fixture
async def core_user():
    from app.utils.password import get_password_hash
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await CoreUser.create(
        email=test_email,
        password_hash=get_password_hash("secret"),
        is_verified=True
    )
    yield user
    await user.delete()
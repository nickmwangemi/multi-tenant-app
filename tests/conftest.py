# tests/conftest.py
import pytest
import asyncpg
import asyncio
import contextlib
import uuid
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
	# Connect using test user credentials
	conn = await asyncpg.connect(
		"postgres://test_user:test_password@localhost:5432/test_core"
	)

	try:
		# Create test tenant databases
		for i in range(1, 3):
			db_name = f"test_tenant_{i}"
			with contextlib.suppress(asyncpg.DuplicateDatabaseError):
				await conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')
				# Initialize schema in tenant database
				tenant_conn = await asyncpg.connect(
					f"postgres://test_user:test_password@localhost:5432/{db_name}"
				)
				await tenant_conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
				await tenant_conn.close()
	finally:
		await conn.close()

	# Initialize core database
	await Tortoise.init(
		db_url="postgres://test_user:test_password@localhost:5432/test_core",
		modules={"models": ["app.models.core", "app.models.tenant", "aerich.models"]},
		_create_db=False
	)
	await Tortoise.generate_schemas()

	yield

	# Cleanup
	await Tortoise.close_connections()


@pytest.fixture
async def test_client():
	from fastapi.testclient import TestClient
	from app.main import app

	# Initialize Tortoise
	await Tortoise.init(
		db_url="postgres://test_user:test_password@localhost:5432/test_core",
		modules={"models": ["app.models.core", "app.models.tenant", "aerich.models"]},
		_create_db=False
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


@pytest.fixture
async def tenant_db():
	return 1  # Return first test tenant ID


import pytest
import asyncpg
import asyncio
from tortoise import Tortoise
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
	policy = asyncio.get_event_loop_policy()
	loop = policy.new_event_loop()
	yield loop
	loop.close()


@pytest.fixture(scope="session", autouse=True)
async def initialize_db():
	# Initialize core database
	await Tortoise.init(
		db_url=settings.database_url,
		modules={
			"models": ["app.models.core", "app.models.tenant", "aerich.models"],
		}
	)
	await Tortoise.generate_schemas()

	# Create test tenant databases
	conn = await asyncpg.connect(settings.database_url)
	for i in range(1, 3):
		db_name = f"test_tenant_{i}"
		try:
			await conn.execute(f'CREATE DATABASE "{db_name}"')
		except asyncpg.DuplicateDatabaseError:
			pass
	await conn.close()

	yield

	# Cleanup
	await Tortoise.close_connections()
	conn = await asyncpg.connect(settings.database_url)
	for i in range(1, 3):
		db_name = f"test_tenant_{i}"
		try:
			await conn.execute(f'DROP DATABASE "{db_name}"')
		except asyncpg.PostgresError:
			pass
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
		}
	)

	with TestClient(app) as client:
		yield client

	await Tortoise.close_connections()
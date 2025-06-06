import pytest
import asyncpg
from fastapi import HTTPException

from app.services.tenant import (
	create_tenant_database,
	init_tenant_schema,
	sync_owner_to_tenant,
)
from app.config import settings
from tortoise import Tortoise

@pytest.mark.asyncio
async def test_create_tenant_database():
	db_name = await create_tenant_database(999)
	assert db_name == "tenant_999"

	# Verify database exists
	conn = await asyncpg.connect(settings.database_url)
	exists = await conn.fetchval(
		"SELECT 1 FROM pg_database WHERE datname = $1", db_name
	)
	await conn.close()
	assert exists == 1


@pytest.mark.asyncio
async def test_init_tenant_schema():
	db_name = "test_tenant_schema"
	conn = await asyncpg.connect(settings.database_url)
	try:
		await conn.execute(f'CREATE DATABASE "{db_name}"')
	except asyncpg.DuplicateDatabaseError:
		pass
	finally:
		await conn.close()

	await init_tenant_schema(db_name)

	# Verify schema exists
	conn = await asyncpg.connect(f"{settings.tenant_database_base}/{db_name}")
	await conn.close()


@pytest.mark.asyncio
async def test_sync_owner_to_tenant(core_user):
	org_id = 999

	# Ensure core database is properly initialized
	await Tortoise.init({
		"connections": {
			"default": settings.database_url
		},
		"apps": {
			"models": {
				"models": ["app.models.core", "aerich.models"],
				"default_connection": "default",
			}
		}
	})

	# Create tenant database and schema
	await create_tenant_database(org_id)
	await init_tenant_schema(f"tenant_{org_id}")

	# Sync owner
	await sync_owner_to_tenant(org_id, core_user.id)

	# Verify in tenant database
	conn = await asyncpg.connect(f"{settings.tenant_database_base}/tenant_{org_id}")
	try:
		user = await conn.fetchrow(
			"SELECT * FROM tenantuser WHERE email = $1",
			core_user.email
		)
		assert user is not None, "Owner not found in tenant database"
		assert user["email"] == core_user.email, "Email mismatch"
	finally:
		await conn.close()


@pytest.mark.asyncio
async def test_sync_nonexistent_owner():
	with pytest.raises(HTTPException):
		await sync_owner_to_tenant(999, 9999)
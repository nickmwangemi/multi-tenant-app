import pytest
import asyncpg
from fastapi import HTTPException

from app.models.tenant import TenantUser
from app.services.tenant import (
	create_tenant_database,
	init_tenant_schema,
	sync_owner_to_tenant,
)
from app.config import settings
from tortoise import Tortoise


@pytest.mark.asyncio
async def test_create_tenant_database():
	# Use admin connection
	admin_conn = await asyncpg.connect(
		"postgres://postgres:postgres@localhost:5432/postgres"
	)
	try:
		db_name = "test_temp_tenant"
		await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
		await admin_conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')

		# Now test the function
		created_name = await create_tenant_database(999)
		assert created_name == "tenant_999"
	finally:
		await admin_conn.close()


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


# In test_services.py
@pytest.mark.asyncio
async def test_sync_owner_to_tenant(core_user):
	# Use admin connection for setup
	admin_conn = await asyncpg.connect(
		"postgres://postgres:postgres@localhost:5432/postgres"
	)
	try:
		org_id = 999
		db_name = f"tenant_{org_id}"
		await admin_conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')

		# Grant permissions on core tables
		await admin_conn.execute(
			f'GRANT SELECT ON TABLE coreuser TO test_user'
		)

		# Now run the test
		await sync_owner_to_tenant(org_id, core_user.id)

		# Verify in tenant database
		tenant_conn = await asyncpg.connect(
			f"postgres://test_user:test_password@localhost:5432/{db_name}"
		)
		try:
			user = await tenant_conn.fetchrow(
				'SELECT * FROM tenantuser WHERE email = $1', core_user.email
			)
			assert user is not None
		finally:
			await tenant_conn.close()
	finally:
		await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
		await admin_conn.close()


@pytest.mark.asyncio
async def test_sync_nonexistent_owner():
	with pytest.raises(HTTPException):
		await sync_owner_to_tenant(999, 9999)
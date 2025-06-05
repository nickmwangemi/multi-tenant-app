import asyncpg

from app.config import settings
from app.db.routing import get_tenant_connection
from app.models.tenant import TenantUser


async def create_tenant_database(organization_id: int):
	"""Create and initialize a new tenant database"""
	conn = await asyncpg.connect(settings.database_url)
	database_name = f"tenant_{organization_id}"
	await conn.execute(f'CREATE DATABASE "{database_name}"')
	await conn.close()

	# Initialize schema
	await init_tenant_schema(database_name)

	return database_name


async def init_tenant_schema(db_name: str):
	"""Run migrations for tenant database"""
	# Use aerich to run migrations
	from aerich import Command
	db_url = f"{settings.database_url.rsplit('/', 1)[0]}/{db_name}"

	command = Command(
		tortoise_config={
			"connections": {"default": db_url},
			"apps": {
				"models": {
					"models": ["app.models.tenant", "aerich.models"],
					"default_connection": "default",
				}
			},
		},
		app="models",
		location="./migrations",
	)
	await command.init()
	await command.upgrade()


async def sync_owner_to_tenant(organization_id: int, owner_id: int):
	"""Sync organization owner to tenant database"""
	conn = await get_tenant_connection(organization_id)
	owner = await CoreUser.get(id=owner_id)

	# Create owner in tenant DB
	await TenantUser.create(
		email=owner.email,
		password_hash=owner.password_hash,
		using_db=conn
	)
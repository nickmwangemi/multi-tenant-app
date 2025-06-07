import asyncpg
from aerich import Command
from fastapi.exceptions import HTTPException
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError, DoesNotExist, IntegrityError

from app.config import settings
from app.db.routing import get_tenant_connection
from app.models.core import CoreUser
from app.models.tenant import TenantUser


async def create_tenant_database(organization_id: int):
    conn = await asyncpg.connect(settings.database_url)
    database_name = f"tenant_{organization_id}"

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", database_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{database_name}"')
        await init_tenant_schema(database_name)
        return database_name
    except asyncpg.PostgresError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create tenant database: {str(e)}"
        )
    finally:
        await conn.close()


async def init_tenant_schema(db_name: str):
    base_url = settings.database_url.rsplit("/", 1)[0]
    db_url = f"{base_url}/{db_name}"

    try:
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
    except ConfigurationError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize tenant schema: {str(e)}"
        ) from e


from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist


async def sync_owner_to_tenant(organization_id: int, owner_id: int):
    core_db = Tortoise.get_connection("default")

    try:
        owner = await CoreUser.get(id=owner_id).using_db(core_db)
    except DoesNotExist as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Core user not found"
        ) from e

    tenant_db_name = f"tenant_{organization_id}"
    tenant_db = await get_tenant_connection(tenant_db_name)

    await TenantUser.create(
        email=owner.email, password_hash=owner.password_hash, is_active=True
    ).using_db(tenant_db)

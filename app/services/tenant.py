import asyncpg
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError, IntegrityError, DoesNotExist
from app.config import settings
from app.models.core import CoreUser
from app.models.tenant import TenantUser
from aerich import Command
from fastapi.exceptions import HTTPException


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


async def sync_owner_to_tenant(organization_id: int, owner_id: int):
    try:
        owner = await CoreUser.get(id=owner_id)
        db_name = f"tenant_{organization_id}"

        # Initialize Tortoise for tenant DB
        await Tortoise.init(
            {
                "connections": {
                    db_name: f"{settings.database_url.rsplit('/', 1)[0]}/{db_name}"
                },
                "apps": {
                    "tenant": {
                        "models": ["app.models.tenant"],
                        "default_connection": db_name,
                    }
                },
            }
        )

        # Create owner in tenant DB
        await TenantUser.create(email=owner.email, password_hash=owner.password_hash)
    except (DoesNotExist, IntegrityError) as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to sync owner to tenant: {str(e)}"
        ) from e
    finally:
        await Tortoise.close_connections()

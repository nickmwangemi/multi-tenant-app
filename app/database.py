from tortoise import Tortoise

from app.config import settings

TORTOISE_ORM = {
    "connections": {
        "default": settings.database_url,
    },
    "apps": {
        "models": {
            "models": ["app.models.core", "app.models.tenant", "aerich.models"],
            "default_connection": "default",
        },
    },
}


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def get_tenant_db(tenant_id: str):
    # Define the database configuration for the tenant
    tenant_db_url = f"postgres://user:password@localhost:5432/tenant_{tenant_id}"
    await Tortoise.init(
        db_url=tenant_db_url,
        modules={'models': ['app.models.tenant']}
    )
    return Tortoise

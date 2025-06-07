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
    "routers": ["app.db.routing.TenantRouter"],
    "use_tz": False,
}


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()

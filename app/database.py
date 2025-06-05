from tortoise import Tortoise
from app.config import settings

async def init_db():
    # Initialize core models only
    await Tortoise.init(
        config={
            "connections": {"default": settings.database_url},
            "apps": {
                "models": {
                    "models": ["app.models.core", "aerich.models"],
                    "default_connection": "default",
                }
            },
        }
    )
    await Tortoise.generate_schemas()
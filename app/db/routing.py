# app/db/routing.py
from fastapi import Request
from tortoise import Tortoise

from app.config import settings


async def get_db_connection(request: Request):
    if getattr(request.state, "is_core", False):
        # Connect to the core database
        await Tortoise.init(
            db_url=settings.core_database_url,
            modules={"models": ["app.models.core"]},
        )
    else:
        # Connect to the tenant-specific database
        tenant_id = request.state.tenant_id
        db_url = f"{settings.tenant_database_url}_{tenant_id}"
        await Tortoise.init(
            db_url=db_url,
            modules={"models": ["app.models.tenant"]},
        )

    return Tortoise.get_connection("default")

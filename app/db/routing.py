from contextvars import ContextVar

from tortoise import Tortoise, connections

from app.config import settings

# Context variable for current tenant
current_tenant = ContextVar("current_tenant", default=None)


class TenantRouter:
    def db_for_read(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"

    def db_for_write(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"


async def init_tenant_connections():
    # Initialize core connection
    await Tortoise.init(
        config={
            "connections": {"default": settings.database_url},
            "apps": {
                "models": {
                    "models": ["app.models.core", "aerich.models"],
                    "default_connection": "default",
                }
            },
            "routers": ["app.db.routing.TenantRouter"],
        }
    )


async def get_tenant_connection(tenant_id: int):
    db_name = f"tenant_{tenant_id}"
    db_url = f"{settings.database_url.rsplit('/', 1)[0]}/{db_name}"

    # Create connection if not exists
    if db_name not in connections:
        await Tortoise.init(
            config={
                "connections": {db_name: db_url},
                "apps": {
                    "tenant": {
                        "models": ["app.models.tenant", "aerich.models"],
                        "default_connection": db_name,
                    }
                },
            },
        )
    return connections.get(db_name)

from contextvars import ContextVar
from tortoise import connections, Tortoise
from app.config import settings

current_tenant = ContextVar("current_tenant", default=None)


class TenantRouter:
    def db_for_read(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"

    def db_for_write(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"


async def get_tenant_connection(tenant_id: int):
    db_name = f"tenant_{tenant_id}"
    db_url = f"{settings.database_url.rsplit('/', 1)[0]}/{db_name}"

    if db_name not in connections:
        await Tortoise.init(
            config={
                "connections": {db_name: db_url},
                "apps": {
                    "tenant": {
                        "models": ["app.models.tenant"],
                        "default_connection": db_name,
                    }
                },
            }
        )
    return connections.get(db_name)

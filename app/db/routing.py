from tortoise import Tortoise, connections
from tortoise.exceptions import ConfigurationError

from app.config import settings
from app.middleware.tenant_context import current_tenant


async def get_tenant_connection(tenant_id: int):
    db_name = f"tenant_{tenant_id}"
    db_url = f"{settings.tenant_database_base}/{db_name}"

    # Check if connection already exists
    if db_name in connections:
        return connections.get(db_name)

    # Initialize new connection
    try:
        await Tortoise.init(
            config={
                "connections": {db_name: db_url},
                "apps": {
                    "tenant": {
                        "models": ["app.models.tenant", "aerich.models"],
                        "default_connection": db_name,
                    }
                },
            }
        )
        connection = connections.get(db_name)
        if connection is None:
            raise ConfigurationError(
                f"Failed to get connection for tenant database {db_name}"
            )
        return connection
    except Exception as e:
        raise ConfigurationError(
            f"Failed to initialize tenant database {db_name}: {str(e)}"
        ) from e


class TenantRouter:
    async def db_for_read(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"

    async def db_for_write(self, model):
        tenant_id = current_tenant.get()
        return f"tenant_{tenant_id}" if tenant_id else "default"

import asyncpg

from app.config import settings


async def create_tenant_database(organization_id: int):
    """
    Create a new tenant database for the organization
    """
    conn = await asyncpg.connect(settings.database_url)

    database_name = f"tenant_{organization_id}"
    await conn.execute(f'CREATE DATABASE "{database_name}"')

    await conn.close()

    return database_name

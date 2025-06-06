import pytest
import asyncpg
from fastapi import HTTPException

from app.services.tenant import (
	create_tenant_database,
	init_tenant_schema,
	sync_owner_to_tenant,
)
from app.models.core import CoreUser
from app.config import settings


@pytest.mark.asyncio
class TestTenantServices:
    async def test_create_tenant_database(self):
        db_name = await create_tenant_database(999)
        assert db_name == "tenant_999"

        # Verify database exists
        conn = await asyncpg.connect(settings.database_url)
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        await conn.close()
        assert exists == 1

    async def test_init_tenant_schema(self):
        await init_tenant_schema("test_tenant_1")
        # Verify schema exists by checking if we can connect
        conn = await asyncpg.connect(f"{settings.tenant_database_base}/test_tenant_1")
        await conn.close()

    async def test_sync_owner_to_tenant(self, core_user):
        org_id = 999
        # Create tenant database first
        await create_tenant_database(org_id)
        await sync_owner_to_tenant(org_id, core_user.id)

        # Verify owner exists in tenant DB
        conn = await asyncpg.connect(f"{settings.tenant_database_base}/tenant_{org_id}")
        user = await conn.fetchrow(
            "SELECT * FROM tenantuser WHERE email = $1", core_user.email
        )
        await conn.close()
        assert user is not None
        assert user["email"] == core_user.email

    async def test_sync_nonexistent_owner(self):
        with pytest.raises(HTTPException):
            await sync_owner_to_tenant(999, 9999)
import pytest
import asyncpg
from fastapi import HTTPException

from app.services.tenant import (
    create_tenant_database,
    init_tenant_schema,
    sync_owner_to_tenant,
)
from app.config import settings


@pytest.mark.asyncio
async def test_create_tenant_database():
    # Use admin connection for setup
    admin_conn = await asyncpg.connect(
        "postgres://postgres:postgres@localhost:5432/postgres"
    )
    try:
        # Ensure test user has permissions
        await admin_conn.execute('GRANT CREATE ON DATABASE postgres TO test_user')

        # Test the function
        db_name = await create_tenant_database(999)
        assert db_name == "tenant_999"
    finally:
        await admin_conn.close()


@pytest.mark.asyncio
async def test_init_tenant_schema():
    db_name = "test_tenant_schema"
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()

    await init_tenant_schema(db_name)

    # Verify schema exists
    conn = await asyncpg.connect(f"{settings.tenant_database_base}/{db_name}")
    await conn.close()




@pytest.mark.asyncio
async def test_sync_owner_to_tenant(core_user):
    admin_conn = await asyncpg.connect(
        "postgres://postgres:postgres@localhost:5432/postgres"
    )
    try:
        org_id = 999
        db_name = f"tenant_{org_id}"

        # Drop if it already exists to prevent conflicts
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin_conn.execute(f'CREATE DATABASE "{db_name}" OWNER test_user')

        # Connect to the new tenant database and create the necessary tables
        tenant_conn = await asyncpg.connect(
            f"postgres://test_user:test_password@localhost:5432/{db_name}"
        )
        try:
            # Create the coreuser table if it does not exist
            await tenant_conn.execute('''
                CREATE TABLE IF NOT EXISTS coreuser (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    -- Add other necessary columns
                )
            ''')

            # Create the tenantuser table if it does not exist
            await tenant_conn.execute('''
                CREATE TABLE IF NOT EXISTS tenantuser (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    -- Add other necessary columns
                )
            ''')

            # Grant permissions if needed
            await admin_conn.execute('GRANT SELECT ON TABLE coreuser TO test_user')

            await sync_owner_to_tenant(org_id, core_user.id)

            # Verify that the user was synced to the tenant database
            user = await tenant_conn.fetchrow(
                'SELECT * FROM tenantuser WHERE email = $1', core_user.email
            )
            assert user is not None
        finally:
            await tenant_conn.close()
    finally:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin_conn.close()



@pytest.mark.asyncio
async def test_sync_nonexistent_owner():
    with pytest.raises(HTTPException) as exc_info:
        await sync_owner_to_tenant(999, 9999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Core user not found"

import uuid

import pytest
import asyncpg
from fastapi import HTTPException

from app.db.routing import get_tenant_connection
from app.models.core import Organization, CoreUser
from app.models.tenant import TenantUser
from app.services.tenant import (
    create_tenant_database,
    init_tenant_schema,
    sync_owner_to_tenant,
)
from app.config import settings

from tortoise import Tortoise

@pytest.mark.asyncio
async def test_create_tenant_database():
    test_id = 999
    db_name = await create_tenant_database(test_id)
    assert db_name == f"tenant_{test_id}"

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

    conn = await asyncpg.connect(f"{settings.tenant_database_base}/{db_name}")
    await conn.close()


@pytest.mark.asyncio
async def test_sync_owner_to_tenant():
    # Initialize database
    await Tortoise.init(
        db_url="postgres://test_user:test_password@localhost:5432/test_core",
        modules={"models": ["app.models.core", "app.models.tenant", "aerich.models"]},
        _create_db=False
    )
    await Tortoise.generate_schemas()

    # Create test user
    from app.utils.password import get_password_hash
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await CoreUser.create(
        email=test_email,
        password_hash=get_password_hash("secret"),
        is_verified=True,
        is_owner=True
    )

    # Create organization
    org = await Organization.create(name="Test Org", owner=user)

    try:
        # Create tenant database
        db_name = await create_tenant_database(org.id)

        # Test sync
        await sync_owner_to_tenant(org.id, user.id)

        # Verify
        tenant_conn = await get_tenant_connection(org.id)
        tenant_user = await TenantUser.get(email=user.email).using_db(tenant_conn)
        assert tenant_user is not None
        assert tenant_user.email == user.email
    finally:
        await Tortoise.close_connections()

@pytest.mark.asyncio
async def test_sync_nonexistent_owner():
    with pytest.raises(HTTPException) as exc_info:
        await sync_owner_to_tenant(999, 9999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Core user not found"

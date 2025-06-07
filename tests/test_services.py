import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, ConfigurationError
from app.services.tenant import (
    create_tenant_database,
    init_tenant_schema,
    sync_owner_to_tenant,
)
from app.config import settings
from app.models.core import CoreUser
from app.models.tenant import TenantUser

@pytest.mark.asyncio
async def test_create_tenant_database_success():
    with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetchval.return_value = None  # Simulate database not existing

        db_name = await create_tenant_database(1)
        assert db_name == "tenant_1"

@pytest.mark.asyncio
async def test_create_tenant_database_existing():
    with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetchval.return_value = 1  # Simulate database existing

        db_name = await create_tenant_database(1)
        assert db_name == "tenant_1"

@pytest.mark.asyncio
async def test_create_tenant_database_error():
    with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetchval.side_effect = asyncpg.PostgresError("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await create_tenant_database(1)

        assert exc_info.value.status_code == 500
        assert "Failed to create tenant database" in exc_info.value.detail

@pytest.mark.asyncio
async def test_init_tenant_schema_success():
    with patch('aerich.Command', new_callable=AsyncMock) as mock_command:
        mock_cmd = AsyncMock()
        mock_command.return_value = mock_cmd

        await init_tenant_schema("test_db")
        mock_cmd.init.assert_awaited_once()
        mock_cmd.upgrade.assert_awaited_once()

@pytest.mark.asyncio
async def test_init_tenant_schema_error():
    with patch('aerich.Command', new_callable=AsyncMock) as mock_command:
        mock_cmd = AsyncMock()
        mock_command.return_value = mock_cmd
        mock_cmd.init.side_effect = ConfigurationError("Config error")

        with pytest.raises(HTTPException) as exc_info:
            await init_tenant_schema("test_db")

        assert exc_info.value.status_code == 500
        assert "Failed to initialize tenant schema" in exc_info.value.detail

@pytest.mark.asyncio
async def test_sync_owner_to_tenant_success():
    with patch('tortoise.Tortoise.get_connection') as mock_get_connection, \
         patch('app.models.core.CoreUser.get', new_callable=AsyncMock) as mock_get, \
         patch('app.db.routing.get_tenant_connection', new_callable=AsyncMock) as mock_tenant_connection, \
         patch('app.models.tenant.TenantUser.create', new_callable=AsyncMock) as mock_create:

        mock_owner = AsyncMock()
        mock_owner.email = "test@example.com"
        mock_owner.password_hash = "hashed_password"
        mock_get.return_value = mock_owner
        mock_tenant_conn = AsyncMock()
        mock_tenant_connection.return_value = mock_tenant_conn

        await sync_owner_to_tenant(1, 1)
        mock_create.assert_awaited_once_with(
            email=mock_owner.email,
            password_hash=mock_owner.password_hash,
            is_active=True
        )

@pytest.mark.asyncio
async def test_sync_owner_to_tenant_error():
    with patch('tortoise.Tortoise.get_connection') as mock_get_connection, \
         patch('app.models.core.CoreUser.get', new_callable=AsyncMock) as mock_get:

        mock_get.side_effect = DoesNotExist("User not found")

        with pytest.raises(HTTPException) as exc_info:
            await sync_owner_to_tenant(1, 1)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Core user not found"

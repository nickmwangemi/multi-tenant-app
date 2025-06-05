import pytest
import asyncpg
from datetime import timedelta
from tortoise import Tortoise

from app.config import settings
from app.main import app
from fastapi.testclient import TestClient
from app.models.core import CoreUser, Organization
from app.models.tenant import TenantUser
from app.utils.auth import create_access_token

client = TestClient(app)


@pytest.fixture(scope="function")
async def tenant_db():
	# Create core user and organization
	user = await CoreUser.create(
		email=f"owner_{id(self)}@example.com",  # Unique email
		password_hash="hash",
		is_verified=True,
		is_owner=True
	)
	org = await Organization.create(name=f"Org_{id(self)}", owner=user)
	org_id = org.id

	# Create tenant database
	db_name = f"tenant_{org_id}"
	conn = await asyncpg.connect(settings.database_url)
	await conn.execute(f'CREATE DATABASE "{db_name}"')
	await conn.close()

	# Initialize tenant models
	await Tortoise.init(
		db_url=f"{settings.database_url.rsplit('/', 1)[0]}/{db_name}",
		modules={"models": ["app.models.tenant", "aerich.models"]},
	)
	await Tortoise.generate_schemas()

	yield {"org_id": org_id, "owner_id": user.id, "db_name": db_name}

	# Cleanup: close connections and drop database
	await Tortoise.close_connections()
	conn = await asyncpg.connect(settings.database_url)
	await conn.execute(f'DROP DATABASE "{db_name}"')
	await conn.close()


@pytest.mark.asyncio
async def test_tenant_user_registration(tenant_db):
	org_id = tenant_db["org_id"]

	response = client.post(
		"/api/auth/register",
		json={"email": "tenant@example.com", "password": "TenantPass123!"},
		headers={"X-TENANT": str(org_id)}
	)

	assert response.status_code == 201
	data = response.json()
	assert data["email"] == "tenant@example.com"
	assert "id" in data


@pytest.mark.asyncio
async def test_tenant_user_login(tenant_db):
	org_id = tenant_db["org_id"]

	# Create tenant user
	response = client.post(
		"/api/auth/register",
		json={"email": "login@example.com", "password": "LoginPass123!"},
		headers={"X-TENANT": str(org_id)}
	)

	# Login
	login_response = client.post(
		"/api/auth/login",
		data={"username": "login@example.com", "password": "LoginPass123!"},
		headers={"X-TENANT": str(org_id)}
	)

	assert login_response.status_code == 200
	assert "access_token" in login_response.json()


@pytest.mark.asyncio
async def test_get_tenant_user_profile(tenant_db):
	org_id = tenant_db["org_id"]

	# Create tenant user
	register_response = client.post(
		"/api/auth/register",
		json={"email": "profile@example.com", "password": "ProfilePass123!"},
		headers={"X-TENANT": str(org_id)}
	)
	user_id = register_response.json()["id"]

	# Login
	login_response = client.post(
		"/api/auth/login",
		data={"username": "profile@example.com", "password": "ProfilePass123!"},
		headers={"X-TENANT": str(org_id)}
	)
	token = login_response.json()["access_token"]

	# Get profile
	profile_response = client.get(
		"/api/users/me",
		headers={
			"Authorization": f"Bearer {token}",
			"X-TENANT": str(org_id)
		}
	)

	assert profile_response.status_code == 200
	data = profile_response.json()
	assert data["id"] == user_id
	assert data["email"] == "profile@example.com"


@pytest.mark.asyncio
async def test_update_tenant_user_profile(tenant_db):
	org_id = tenant_db["org_id"]

	# Create tenant user
	register_response = client.post(
		"/api/auth/register",
		json={"email": "update@example.com", "password": "UpdatePass123!"},
		headers={"X-TENANT": str(org_id)}
	)
	user_id = register_response.json()["id"]

	# Login
	login_response = client.post(
		"/api/auth/login",
		data={"username": "update@example.com", "password": "UpdatePass123!"},
		headers={"X-TENANT": str(org_id)}
	)
	token = login_response.json()["access_token"]

	# Update profile
	new_email = "updated@example.com"
	update_response = client.put(
		"/api/users/me",
		json={"email": new_email},
		headers={
			"Authorization": f"Bearer {token}",
			"X-TENANT": str(org_id)
		}
	)

	assert update_response.status_code == 200
	assert update_response.json()["email"] == new_email

	# Verify update
	profile_response = client.get(
		"/api/users/me",
		headers={
			"Authorization": f"Bearer {token}",
			"X-TENANT": str(org_id)
		}
	)
	assert profile_response.json()["email"] == new_email


@pytest.mark.asyncio
async def test_tenant_isolation(tenant_db):
	org1_id = tenant_db["org_id"]

	# Create second organization
	owner = await CoreUser.get(id=tenant_db["owner_id"])
	org2 = await Organization.create(name="Org 2", owner=owner)
	org2_id = org2.id

	# Create tenant database for second org
	db_name2 = f"tenant_{org2_id}"
	conn = await asyncpg.connect(settings.database_url)
	await conn.execute(f'CREATE DATABASE "{db_name2}"')
	await conn.close()

	# Initialize tenant models for second org
	await Tortoise.init(
		db_url=f"{settings.database_url.rsplit('/', 1)[0]}/{db_name2}",
		modules={"models": ["app.models.tenant", "aerich.models"]},
	)
	await Tortoise.generate_schemas()

	# Create user in first tenant
	user1 = client.post(
		"/api/auth/register",
		json={"email": "isolated@example.com", "password": "pass123"},
		headers={"X-TENANT": str(org1_id)}
	).json()

	# Create user in second tenant
	user2 = client.post(
		"/api/auth/register",
		json={"email": "isolated@example.com", "password": "pass123"},
		headers={"X-TENANT": str(org2_id)}
	).json()

	# Verify different users
	assert user1["id"] != user2["id"]

	# Cleanup second tenant
	await Tortoise.close_connections()
	conn = await asyncpg.connect(settings.database_url)
	await conn.execute(f'DROP DATABASE "{db_name2}"')
	await conn.close()
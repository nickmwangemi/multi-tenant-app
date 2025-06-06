import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.main import app
from app.config import settings
from app.models.core import CoreUser

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
async def initialize_tests():
	await Tortoise.init(
		db_url=settings.database_url,
		modules={"models": ["app.models.core"]},
	)
	await Tortoise.generate_schemas()
	yield
	await Tortoise._drop_databases()


@pytest.mark.asyncio
async def test_register_user():
	response = client.post(
		"/api/auth/register",
		json={
			"email": "test@example.com",
			"password": "SecurePass123!",
			"is_owner": True
		}
	)
	assert response.status_code == 201
	data = response.json()
	assert "user" in data
	assert "access_token" in data
	assert "verification_token" in data


@pytest.mark.asyncio
async def test_login_user():
	# Create test user
	await CoreUser.create(
		email="login@test.com",
		password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPVgaYl5O",  # bcrypt for "secret"
		is_verified=True
	)

	response = client.post(
		"/api/auth/login",
		data={"email": "login@test.com", "password": "secret"}
	)
	assert response.status_code == 200
	assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_create_organization():
	# Create owner user
	owner = await CoreUser.create(
		email="owner@org.com",
		password_hash="hashed_password",
		is_owner=True,
		is_verified=True
	)

	# Get token
	login_res = client.post(
		"/api/auth/login",
		data={"email": "owner@org.com", "password": "secret"}
	)
	token = login_res.json()["access_token"]

	# Create organization
	response = client.post(
		"/api/organizations",
		headers={"Authorization": f"Bearer {token}"},
		json={"name": "Test Org"}
	)
	assert response.status_code == 200
	data = response.json()
	assert "organization_id" in data
	assert "tenant_db_name" in data
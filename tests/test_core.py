import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.core import CoreUser


@pytest.fixture
async def client():
	from tortoise import Tortoise
	from app.config import settings

	await Tortoise.init(
		db_url=settings.database_url,
		modules={"models": ["app.models.core"]}
	)
	await Tortoise.generate_schemas()

	with TestClient(app) as client:
		yield client

	await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_register_user(client):
	response = client.post(
		"/api/auth/register",
		json={
			"email": "test@example.com",
			"password": "SecurePass123!",
			"is_owner": True,
		},
	)
	assert response.status_code == 201
	data = response.json()
	assert "user" in data
	assert "access_token" in data


@pytest.mark.asyncio
async def test_login_user(client):
	# Create test user
	await CoreUser.create(
		email="login@test.com",
		password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPVgaYl5O",  # "secret"
		is_verified=True,
	)

	response = client.post(
		"/api/auth/login",
		data={"email": "login@test.com", "password": "secret"}
	)
	assert response.status_code == 200
	assert "access_token" in response.json()
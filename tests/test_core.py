import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.config import settings
from app.main import app
from app.models.core import CoreUser, Organization
from app.utils.auth import create_access_token

# Test client
client = TestClient(app)

# Test data
TEST_USER = {
	"email": "test@example.com",
	"password": "TestPass123!",
	"is_owner": True
}


@pytest.mark.asyncio
async def test_user_registration():
	response = client.post("/api/auth/register", json=TEST_USER)
	assert response.status_code == 201
	data = response.json()
	assert data["user"]["email"] == TEST_USER["email"]
	assert "access_token" in data
	assert "verification_token" in data


@pytest.mark.asyncio
async def test_email_verification():
	# First register a user
	reg_response = client.post("/api/auth/register", json=TEST_USER)
	token = reg_response.json()["verification_token"]

	# Verify email
	response = client.get(f"/api/auth/verify?token={token}")
	assert response.status_code == 200
	assert response.json()["message"] == "Email verified successfully"

	# Verify user is updated
	user = await CoreUser.get(email=TEST_USER["email"])
	assert user.is_verified is True


@pytest.mark.asyncio
async def test_user_login():
	# Register and verify
	reg_response = client.post("/api/auth/register", json=TEST_USER)
	token = reg_response.json()["verification_token"]
	client.get(f"/api/auth/verify?token={token}")

	# Login
	response = client.post("/api/auth/login", json={
		"email": TEST_USER["email"],
		"password": TEST_USER["password"]
	})

	assert response.status_code == 200
	assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_organization_creation():
	# Register, verify and login
	reg_response = client.post("/api/auth/register", json=TEST_USER)
	token = reg_response.json()["verification_token"]
	client.get(f"/api/auth/verify?token={token}")
	login_response = client.post("/api/auth/login", json={
		"email": TEST_USER["email"],
		"password": TEST_USER["password"]
	})
	access_token = login_response.json()["access_token"]

	# Create organization
	response = client.post(
		"/api/organizations",
		json={"name": "Test Org"},
		headers={"Authorization": f"Bearer {access_token}"}
	)

	assert response.status_code == 200
	data = response.json()
	assert data["organization_id"] > 0
	assert data["tenant_db_name"].startswith("tenant_")

	# Verify organization in DB
	org = await Organization.get_or_none(id=data["organization_id"])
	assert org is not None
	assert org.name == "Test Org"


@pytest.mark.asyncio
async def test_organization_creation_non_owner():
	# Create non-owner user
	user_data = TEST_USER.copy()
	user_data["is_owner"] = False
	reg_response = client.post("/api/auth/register", json=user_data)
	token = reg_response.json()["verification_token"]
	client.get(f"/api/auth/verify?token={token}")
	login_response = client.post("/api/auth/login", json={
		"email": user_data["email"],
		"password": user_data["password"]
	})
	access_token = login_response.json()["access_token"]

	# Attempt to create organization
	response = client.post(
		"/api/organizations",
		json={"name": "Should Fail"},
		headers={"Authorization": f"Bearer {access_token}"}
	)

	assert response.status_code == 403
	assert "Only owners can create organizations" in response.json()["detail"]
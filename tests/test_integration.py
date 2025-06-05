import pytest
import asyncpg
from tortoise import Tortoise

from app.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.asyncio
async def test_full_workflow():
	# Step 1: Register owner
	register_response = client.post("/api/auth/register", json={
		"email": "workflow@example.com",
		"password": "WorkflowPass123!",
		"is_owner": True
	})
	assert register_response.status_code == 201
	register_data = register_response.json()
	verification_token = register_data["verification_token"]

	# Step 2: Verify email
	verify_response = client.get(f"/api/auth/verify?token={verification_token}")
	assert verify_response.status_code == 200

	# Step 3: Login as owner
	login_response = client.post("/api/auth/login", json={
		"email": "workflow@example.com",
		"password": "WorkflowPass123!"
	})
	assert login_response.status_code == 200
	owner_token = login_response.json()["access_token"]

	# Step 4: Create organization
	org_response = client.post(
		"/api/organizations",
		json={"name": "Workflow Org"},
		headers={"Authorization": f"Bearer {owner_token}"}
	)
	assert org_response.status_code == 200
	org_data = org_response.json()
	org_id = org_data["organization_id"]

	# Step 5: Register tenant user
	tenant_register = client.post(
		"/api/auth/register",
		json={"email": "employee@example.com", "password": "EmployeePass123!"},
		headers={"X-TENANT": str(org_id)}
	)
	assert tenant_register.status_code == 201
	tenant_user_id = tenant_register.json()["id"]

	# Step 6: Login as tenant user
	tenant_login = client.post(
		"/api/auth/login",
		data={
			"username": "employee@example.com",
			"password": "EmployeePass123!"
		},
		headers={"X-TENANT": str(org_id)}
	)
	assert tenant_login.status_code == 200
	tenant_token = tenant_login.json()["access_token"]

	# Step 7: Access profile
	profile_response = client.get(
		"/api/users/me",
		headers={
			"Authorization": f"Bearer {tenant_token}",
			"X-TENANT": str(org_id)
		}
	)
	assert profile_response.status_code == 200
	assert profile_response.json()["email"] == "employee@example.com"

	# Step 8: Update profile
	update_response = client.put(
		"/api/users/me",
		json={"email": "updated.employee@example.com"},
		headers={
			"Authorization": f"Bearer {tenant_token}",
			"X-TENANT": str(org_id)
		}
	)
	assert update_response.status_code == 200
	assert update_response.json()["email"] == "updated.employee@example.com"


@pytest.mark.asyncio
async def test_cross_tenant_access():
	# Create first organization
	reg_response1 = client.post("/api/auth/register", json={
		"email": "owner1@example.com",
		"password": "Pass123!",
		"is_owner": True
	})
	token1 = reg_response1.json()["verification_token"]
	client.get(f"/api/auth/verify?token={token1}")
	login1 = client.post("/api/auth/login", json={
		"email": "owner1@example.com",
		"password": "Pass123!"
	})
	owner_token1 = login1.json()["access_token"]
	org1 = client.post(
		"/api/organizations",
		json={"name": "Org 1"},
		headers={"Authorization": f"Bearer {owner_token1}"}
	).json()

	# Create second organization
	reg_response2 = client.post("/api/auth/register", json={
		"email": "owner2@example.com",
		"password": "Pass123!",
		"is_owner": True
	})
	token2 = reg_response2.json()["verification_token"]
	client.get(f"/api/auth/verify?token={token2}")
	login2 = client.post("/api/auth/login", json={
		"email": "owner2@example.com",
		"password": "Pass123!"
	})
	owner_token2 = login2.json()["access_token"]
	org2 = client.post(
		"/api/organizations",
		json={"name": "Org 2"},
		headers={"Authorization": f"Bearer {owner_token2}"}
	).json()

	# Create user in first organization
	tenant1 = client.post(
		"/api/auth/register",
		json={"email": "user1@example.com", "password": "pass123"},
		headers={"X-TENANT": str(org1["organization_id"])}
	).json()

	# Create token for user in first organization
	login_tenant1 = client.post(
		"/api/auth/login",
		data={"username": "user1@example.com", "password": "pass123"},
		headers={"X-TENANT": str(org1["organization_id"])}
	).json()
	tenant_token1 = login_tenant1["access_token"]

	# Try to access with same token but different tenant header
	response = client.get(
		"/api/users/me",
		headers={
			"Authorization": f"Bearer {tenant_token1}",
			"X-TENANT": str(org2["organization_id"])
		}
	)

	# Should fail since user doesn't exist in second tenant
	assert response.status_code == 401
	assert "Could not validate credentials" in response.json()["detail"]
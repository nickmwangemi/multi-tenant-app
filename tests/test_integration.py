import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.main import app
from app.config import settings
from app.models.core import CoreUser

client = TestClient(app)


@pytest.mark.asyncio
class TestIntegration:
	async def test_full_flow(self):
		# Register core user
		register_res = client.post(
			"/api/auth/register",
			json={
				"email": "integration@test.com",
				"password": "IntegrationPass123!",
				"is_owner": True
			}
		)
		assert register_res.status_code == 201
		register_data = register_res.json()

		# Verify email
		verify_res = client.get(
			f"/api/auth/verify?token={register_data['verification_token']}"
		)
		assert verify_res.status_code == 200

		# Login
		login_res = client.post(
			"/api/auth/login",
			data={"email": "integration@test.com", "password": "IntegrationPass123!"}
		)
		assert login_res.status_code == 200
		token = login_res.json()["access_token"]

		# Create organization
		org_res = client.post(
			"/api/organizations",
			headers={"Authorization": f"Bearer {token}"},
			json={"name": "Integration Test Org"}
		)
		assert org_res.status_code == 200
		org_data = org_res.json()

		# Register tenant user
		tenant_res = client.post(
			"/api/auth/register",
			headers={"X-TENANT": str(org_data["organization_id"])},
			json={
				"email": "tenant@integration.com",
				"password": "TenantPass123!"
			}
		)
		assert tenant_res.status_code == 201

		# Login tenant user
		tenant_login = client.post(
			"/api/auth/login",
			headers={"X-TENANT": str(org_data["organization_id"])},
			data={"email": "tenant@integration.com", "password": "TenantPass123!"}
		)
		assert tenant_login.status_code == 200
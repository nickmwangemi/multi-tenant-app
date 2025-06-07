import uuid
import pytest
from fastapi import status
from tortoise import Tortoise

@pytest.mark.asyncio
async def test_full_flow(test_client):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@integration.com"

    register_res = await test_client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "ValidPass123!",
            "is_owner": True
        }
    )
    assert register_res.status_code == status.HTTP_201_CREATED
    register_data = register_res.json()

    token = register_data["access_token"]

    verify_res = await test_client.get(
        f"/api/auth/verify?token={register_data['verification_token']}"
    )
    assert verify_res.status_code == status.HTTP_200_OK

    login_res = await test_client.post(
        "/api/auth/login",
        data={"username": unique_email, "password": "ValidPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_res.status_code == status.HTTP_200_OK

    org_res = await test_client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Integration Test Org"}
    )

    if org_res.status_code != status.HTTP_200_OK:
        print(f"Organization creation failed: {org_res.json()}")

    assert org_res.status_code == status.HTTP_200_OK
    org_data = org_res.json()

    tenant_email = org_data["tenant_email"]
    tenant_res = await test_client.post(
        "/api/auth/register",
        headers={"X-TENANT": str(org_data["organization_id"])},
        json={
            "email": tenant_email,
            "password": "TenantPass123!"
        }
    )

    if tenant_res.status_code != status.HTTP_201_CREATED:
        print(f"Tenant registration failed: {tenant_res.json()}")
    assert tenant_res.status_code == status.HTTP_201_CREATED

    await Tortoise.init({
        "connections": {
            "tenant": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "database": f"tenant_{org_data['organization_id']}",
                    "host": "localhost",
                    "password": "postgres",
                    "port": 5432,
                    "user": "postgres"
                }
            }
        },
        "apps": {
            "tenant": {
                "models": ["app.models.tenant"],
                "default_connection": "tenant",
            }
        },
    })

    try:
        from app.models.tenant import TenantUser
        user = await TenantUser.get(email=tenant_email)
        assert user is not None
    finally:
        await Tortoise.close_connections()

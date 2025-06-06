import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_full_flow(test_client):
    # Generate unique test data
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@integration.com"
    tenant_email = f"tenant_{uuid.uuid4().hex[:8]}@integration.com"

    # 1. Register core user
    register_res = test_client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "ValidPass123!",
            "is_owner": True
        }
    )
    assert register_res.status_code == status.HTTP_201_CREATED
    register_data = register_res.json()

    # 2. Verify email
    verify_res = test_client.get(
        f"/api/auth/verify?token={register_data['verification_token']}"
    )
    assert verify_res.status_code == status.HTTP_200_OK

    # 3. Login
    login_res = test_client.post(
        "/api/auth/login",
        data={"username": unique_email, "password": "ValidPass123!"},  # Changed from json to data
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_res.status_code == status.HTTP_200_OK

    # 4. Create organization
    org_res = test_client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Integration Test Org"}
    )

    # Debug output
    if org_res.status_code != status.HTTP_200_OK:
        print(f"Organization creation failed: {org_res.json()}")

    assert org_res.status_code == status.HTTP_200_OK
    org_data = org_res.json()

    # 5. Register tenant user (using sync client)
    tenant_res = test_client.post(
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

    # 6. Verify tenant user exists (using proper async connection)
    from tortoise import Tortoise
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

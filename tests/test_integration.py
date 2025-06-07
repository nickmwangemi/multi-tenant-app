import uuid

import pytest
from fastapi import status
from tortoise import Tortoise


# tests/test_integration.py
async def test_full_flow(test_client):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@integration.com"

    # Register
    register_res = test_client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "ValidPass123!", "is_owner": True},
    )
    assert register_res.status_code == status.HTTP_201_CREATED
    register_data = register_res.json()

    # Verify email
    verify_res = test_client.get(
        f"/api/auth/verify?token={register_data['verification_token']}"
    )
    assert verify_res.status_code == status.HTTP_200_OK

    # Login (use form data format)
    login_res = test_client.post(
        "/api/auth/login",
        data={"username": unique_email, "password": "ValidPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == status.HTTP_200_OK
    token = login_res.json()["access_token"]

    # Create organization
    org_res = test_client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Integration Test Org"},
    )
    assert org_res.status_code == status.HTTP_200_OK
    org_data = org_res.json()

    # Register tenant user
    tenant_email = f"tenant_{unique_email}"
    tenant_res = test_client.post(
        "/api/auth/register",
        headers={"X-TENANT": str(org_data["organization_id"])},
        json={"email": tenant_email, "password": "TenantPass123!"},
    )
    assert tenant_res.status_code == status.HTTP_201_CREATED

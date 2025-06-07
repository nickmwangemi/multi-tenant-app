import uuid

import pytest


@pytest.mark.asyncio
async def test_register_user(test_client):
    unique_email = f"test_{uuid.uuid4().hex}@example.com"

    response = test_client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "ValidPass123!",
            "is_owner": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_user(test_client, core_user):
    core_user.is_verified = True
    await core_user.save()

    response = await test_client.post(
        "/api/auth/login", data={"username": core_user.email, "password": "secret"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_verify_email(test_client, core_user):
    core_user.verification_token = "test_token"
    await core_user.save()

    response = test_client.get("/api/auth/verify?token=test_token")
    assert response.status_code == 200
    assert "Email verified successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_verify_email_invalid_token(test_client):
    response = test_client.get("/api/auth/verify?token=invalid")
    assert response.status_code == 404

# tests/test_core.py
import pytest


@pytest.mark.asyncio
async def test_register_user(test_client):
    # Use a truly unique email
    import uuid
    unique_email = f"test_{uuid.uuid4().hex}@example.com"

    response = test_client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "ValidPass123!",  # Ensure it meets all requirements
            "is_owner": True,
        },
    )

    # Debug output
    if response.status_code != 201:
        print(f"Registration failed: {response.json()}")

    assert response.status_code == 201, \
        f"Expected 201 Created, got {response.status_code}. Response: {response.json()}"

    data = response.json()
    assert "user" in data, "Response missing user data"
    assert "access_token" in data, "Response missing access token"

@pytest.mark.asyncio
async def test_login_user(test_client, core_user):
    # Verify email first
    core_user.is_verified = True
    await core_user.save()

    response = test_client.post(
        "/api/auth/login",
        data={"email": "test@example.com", "password": "secret"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
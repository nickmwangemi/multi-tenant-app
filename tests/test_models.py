import pytest


from app.models.core import CoreUser, Organization


import uuid

@pytest.mark.asyncio
async def test_core_user_verification():
    email = f"{uuid.uuid4()}@example.com"
    user = await CoreUser.create_user(
        email=email,
        password_hash="hash",
        verification_token="token"
    )
    assert not user.is_verified
    user.is_verified = True
    await user.save()
    assert user.is_verified


@pytest.mark.asyncio
async def test_organization_creation(core_user):
    org = await Organization.create(name="Test Org", owner=core_user)
    assert org.name == "Test Org"
    assert org.owner_id == core_user.id
import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.testclient import TestClient

from app.middleware.tenant_context import TenantMiddleware, get_current_tenant, set_current_tenant, reset_current_tenant

app = FastAPI()
app.add_middleware(TenantMiddleware)


@app.get("/")
async def root(request: Request):
    return {"is_core": request.state.is_core, "tenant": request.state.tenant}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, {"is_core": True, "tenant": None}),
        ("1", {"is_core": False, "tenant": "1"}),
    ],
)
def test_tenant_middleware(client, header, expected):
    headers = {}
    if header is not None:
        headers["X-TENANT"] = header

    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert response.json() == expected



def test_invalid_tenant_id(client):
    with pytest.raises(HTTPException) as exc_info:
        client.get("/", headers={"X-TENANT": "invalid"})
    assert exc_info.value.status_code == 400
    assert "Invalid tenant ID format" in exc_info.value.detail



def test_get_current_tenant():
    # Test with no tenant set
    assert get_current_tenant() is None

    # Set a tenant ID in the context
    tenant_id = 1
    token = set_current_tenant(tenant_id)

    # Test that the function returns the correct tenant ID
    assert get_current_tenant() == tenant_id

    # Reset the tenant context
    reset_current_tenant(token)

    # Test that the context is reset correctly
    assert get_current_tenant() is None

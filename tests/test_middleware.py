import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.tenant_context import TenantMiddleware

app = FastAPI()
app.add_middleware(TenantMiddleware)


@app.get("/")
async def root(request: Request):
	return {
		"is_core": request.state.is_core,
		"tenant": request.state.tenant
	}


client = TestClient(app)


@pytest.mark.parametrize("header,expected", [
	(None, {"is_core": True, "tenant": None}),
	("1", {"is_core": False, "tenant": "1"}),
	("abc", {"is_core": True, "tenant": "abc"}),  # Should still set tenant even if invalid
])
def test_tenant_middleware(header, expected):
	headers = {}
	if header is not None:
		headers["X-TENANT"] = header

	response = client.get("/", headers=headers)
	assert response.status_code == 200
	assert response.json() == expected


def test_invalid_tenant_id():
	with pytest.raises(ValueError):
		client.get("/", headers={"X-TENANT": "invalid"})
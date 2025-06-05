from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_tenant = request.headers.get("X-TENANT")
        request.state.tenant = x_tenant

        request.state.is_core = not x_tenant
        return await call_next(request)

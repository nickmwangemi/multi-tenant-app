from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.routing import current_tenant

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_tenant = request.headers.get("X-TENANT")
        request.state.tenant = x_tenant
        request.state.is_core = not x_tenant

        if x_tenant:
            try:
                tenant_id = int(x_tenant)
                token = current_tenant.set(tenant_id)
                response = await call_next(request)
                current_tenant.reset(token)
                return response
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid tenant ID format. Must be an integer."
                ) from e
        return await call_next(request)
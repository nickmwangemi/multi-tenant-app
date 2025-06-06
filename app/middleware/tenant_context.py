from contextvars import ContextVar
from typing import Optional
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException, Request


# Context variable to store the current tenant ID
current_tenant: ContextVar[Optional[int]] = ContextVar("current_tenant", default=None)
current_tenant_token: ContextVar[Optional[uuid.UUID]] = ContextVar("current_tenant_token", default=None)

def get_current_tenant() -> Optional[int]:
    """Get the current tenant ID from context"""
    return current_tenant.get()

def set_current_tenant(tenant_id: int) -> uuid.UUID:
    """Set the current tenant ID in context and return the reset token"""
    token = current_tenant.set(tenant_id)
    current_tenant_token.set(token)
    return token

def reset_current_tenant(token: uuid.UUID) -> None:
    """Reset the current tenant context to its previous state"""
    if current_tenant_token.get() == token:
        current_tenant.reset(token)
        current_tenant_token.set(None)

class TenantContext:
    """Context manager for tenant context"""
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.token = None

    async def __aenter__(self):
        self.token = set_current_tenant(self.tenant_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            reset_current_tenant(self.token)



class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_tenant = request.headers.get("X-TENANT")
        request.state.tenant = x_tenant
        request.state.is_core = not x_tenant

        if not x_tenant:
            return await call_next(request)

        try:
            tenant_id = int(x_tenant)
            async with TenantContext(tenant_id):
                response = await call_next(request)
                return response
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid tenant ID format. Must be an integer.",
            ) from e
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise

from app.database import init_db
from app.db.routing import init_tenant_connections
from app.middleware.tenant_context import TenantMiddleware
from app.routes.core import router as core_router
from app.routes.tenant import router as tenant_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_tenant_connections()
    yield
    await Tortoise.close_connections()

app = FastAPI(lifespan=lifespan)
app.add_middleware(TenantMiddleware)
app.include_router(core_router)
app.include_router(tenant_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
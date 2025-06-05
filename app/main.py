from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.database import init_db
from app.routes import core, tenant


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await Tortoise.close_connections()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.include_router(core.router, prefix="/api", tags=["core"])
app.include_router(tenant.router, prefix="/api", tags=["tenant"])

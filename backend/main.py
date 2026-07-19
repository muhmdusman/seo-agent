from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import settings
from db.dbconfig import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db()
    print("✅ Database connected")

    yield

    print("👋 Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
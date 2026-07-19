from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import settings
from db.dbconfig import check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_db_connection()
    print("✅ Database connected")

    yield

    print("👋 Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
from contextlib import asynccontextmanager
from core.redis_config import redis_client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from api.main import router as api_router
from core.config import settings
from db.dbconfig import get_db
from db.dbconfig import engine
import logging



@asynccontextmanager
async def lifespan(app: FastAPI):

    get_db()

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    print("✅ Database connected")

    await redis_client.ping()
    print("connected to redis")

    yield
    await redis_client.aclose()

    await engine.dispose()
    print("👋 Database engine disposed")

    print("👋 Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app.include_router(api_router)
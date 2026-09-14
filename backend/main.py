import asyncio
import sys

# psycopg's async driver does not support Windows' default Proactor event loop,
# so the policy has to be set before uvicorn creates the loop. Importing this
# module early enough is what makes `uvicorn main:app` work on Windows.
# The Celery worker sets the same policy independently in workers/.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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



logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    get_db()

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    # Plain ASCII on purpose: the Windows console defaults to cp1252, where
    # printing non-encodable characters raises UnicodeEncodeError and takes
    # the whole application startup down with it.
    logger.info("Database connected")

    await redis_client.ping()
    logger.info("Redis connected")

    yield

    await redis_client.aclose()
    await engine.dispose()
    logger.info("Database engine disposed, application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "ok"}

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
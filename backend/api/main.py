from fastapi import APIRouter

from api.routes.auth import router as auth_router
from api.routes.search_console import router as search_console_router
router = APIRouter(
    prefix="/api/v1",
)

router.include_router(auth_router)
router.include_router(search_console_router)
from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["Health"],
)

api_router.include_router(
    auth_router,
    tags=["Authentication"],
)

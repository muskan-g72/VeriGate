from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.api.routes.test_cases import router as test_cases_router
from app.api.routes.test_suites import router as test_suites_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["Health"],
)

api_router.include_router(
    auth_router,
    tags=["Authentication"],
)

api_router.include_router(
    projects_router,
    tags=["Projects"],
)

api_router.include_router(
    test_suites_router,
    tags=["Test Suites"],
)

api_router.include_router(
    test_cases_router,
    tags=["Test Cases"],
)

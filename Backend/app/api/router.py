from fastapi import APIRouter
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.admin import router as admin_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.issues import router as issues_router
from app.api.routes.members import router as members_router
from app.api.routes.projects import router as projects_router
from app.api.routes.reports import router as reports_router
from app.api.routes.teams import router as teams_router
from app.api.routes.test_cases import router as test_cases_router
from app.api.routes.test_suites import router as test_suites_router
from app.api.routes.verification_runs import router as verification_runs_router

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
    members_router,
    tags=["Members"],
)

api_router.include_router(
    teams_router,
    tags=["Teams"],
)

api_router.include_router(
    test_suites_router,
    tags=["Test Suites"],
)

api_router.include_router(
    test_cases_router,
    tags=["Test Cases"],
)

api_router.include_router(
    verification_runs_router,
    tags=["Verification Runs"],
)

api_router.include_router(
    issues_router,
    tags=["Issues"],
)

api_router.include_router(
    reports_router,
    tags=["Reports"],
)

api_router.include_router(
    audit_logs_router,
    tags=["Audit Logs"],
)
api_router.include_router(
    dashboard_router,
    tags=["Dashboard"],
)
api_router.include_router(
    admin_router,
    tags=["Admin"],
)
api_router.include_router(
    evidence_router,
    tags=["Evidence"],
)
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.permissions import VIEW_PROJECT_ROLES, get_accessible_project
from app.db.session import get_db
from app.schemas.report import (
    IssueReportResponse,
    ProjectReportResponse,
    VerificationTrendPoint,
)
from app.services.report_service import (
    build_issue_report,
    build_project_report,
    build_verification_trend,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/reports",
    response_model=ProjectReportResponse,
)
def get_project_report(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        VIEW_PROJECT_ROLES,
    )
    return build_project_report(database_session, project_id)


@router.get(
    "/projects/{project_id}/reports/verification-trend",
    response_model=list[VerificationTrendPoint],
)
def get_verification_trend(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        VIEW_PROJECT_ROLES,
    )
    return build_verification_trend(database_session, project_id)


@router.get(
    "/projects/{project_id}/reports/issues",
    response_model=IssueReportResponse,
)
def get_issue_report(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        VIEW_PROJECT_ROLES,
    )
    return build_issue_report(database_session, project_id)

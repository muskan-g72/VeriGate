import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.verification_runs import get_owned_verification_run
from app.core.permissions import VIEW_PROJECT_ROLES, get_accessible_project
from app.db.session import get_db
from app.schemas.report import (
    IssueReportResponse,
    ProjectReportResponse,
    VerificationTrendPoint,
)
from app.services.report_generator import (
    build_verification_run_report_data,
    generate_verification_report_html,
    generate_verification_report_pdf,
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


@router.get("/verification-runs/{verification_run_id}/report")
@router.get("/verification-runs/{verification_run_id}/reports")
@router.get("/reports/verification/{verification_run_id}")
@router.get("/reports/verification-runs/{verification_run_id}")
@router.get("/reports/{verification_run_id}")
@router.get("/reports/{verification_run_id}/report")
async def get_verification_run_report(
    verification_run_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    format: str = "pdf",
):
    """Generate and download Proof of Verification report for a verification run."""
    verification_run = get_owned_verification_run(
        verification_run_id,
        current_user.id,
        database_session,
    )

    report_data = await build_verification_run_report_data(
        database_session,
        verification_run,
        current_user,
    )

    if format.lower() == "json":
        return report_data

    if format.lower() == "html":
        html_content = generate_verification_report_html(report_data)
        return HTMLResponse(content=html_content)

    # PDF format
    try:
        pdf_bytes = await generate_verification_report_pdf(report_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification report PDF generation failed: {exc}",
        ) from exc

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", verification_run.name).strip("_")
    filename = (
        f"verigate-proof-of-verification-{safe_name or verification_run_id}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

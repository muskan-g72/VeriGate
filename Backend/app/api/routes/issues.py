import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.projects import get_owned_project
from app.api.routes.verification_runs import get_owned_verification_result
from app.core.permissions import (
    EXECUTE_VERIFICATION_ROLES,
    MANAGE_PROJECT_ROLES,
    VIEW_PROJECT_ROLES,
)
from app.db.session import get_db
from app.models.issue import Issue
from app.schemas.issue import IssueCreate, IssueRead, IssueUpdate
from app.services.audit_service import record_audit_event

router = APIRouter()


def get_owned_issue(
    issue_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> Issue:
    issue = database_session.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    get_owned_project(issue.project_id, owner_id, database_session)
    return issue


@router.post(
    "/verification-results/{verification_result_id}/issues",
    response_model=IssueRead,
    status_code=status.HTTP_201_CREATED,
)
def create_issue(
    verification_result_id: uuid.UUID,
    issue_data: IssueCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Issue:
    verification_result = get_owned_verification_result(
        verification_result_id,
        current_user.id,
        database_session,
        EXECUTE_VERIFICATION_ROLES,
    )
    if verification_result.status not in {"failed", "blocked"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issues can only be created from failed or blocked results",
        )

    project_id = verification_result.verification_run.test_suite.project_id
    issue = Issue(
        project_id=project_id,
        verification_result_id=verification_result.id,
        test_case_id=verification_result.test_case_id,
        verification_run_id=verification_result.verification_run_id,
        reported_by_id=current_user.id,
        **issue_data.model_dump(),
    )
    database_session.add(issue)
    database_session.flush()
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project_id,
        action="created",
        resource_type="issue",
        resource_id=issue.id,
        description=f"Created issue '{issue.title}'",
    )
    database_session.commit()
    database_session.refresh(issue)
    return issue


@router.get("/projects/{project_id}/issues", response_model=list[IssueRead])
def list_issues(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Issue]:
    project = get_owned_project(project_id, current_user.id, database_session)
    return list(
        database_session.scalars(
            select(Issue)
            .where(Issue.project_id == project.id)
            .order_by(Issue.created_at.desc())
        )
    )


@router.get("/issues/{issue_id}", response_model=IssueRead)
def read_issue(
    issue_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Issue:
    return get_owned_issue(issue_id, current_user.id, database_session)


@router.patch("/issues/{issue_id}", response_model=IssueRead)
def update_issue(
    issue_id: uuid.UUID,
    issue_data: IssueUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Issue:
    issue = get_owned_issue(issue_id, current_user.id, database_session)
    get_owned_project(
        issue.project_id,
        current_user.id,
        database_session,
        MANAGE_PROJECT_ROLES,
    )
    for field, value in issue_data.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)

    if issue_data.status in {"resolved", "closed"}:
        issue.resolved_at = issue.resolved_at or datetime.now(UTC)
        record_audit_event(
            database_session,
            user_id=current_user.id,
            project_id=issue.project_id,
            action="resolved",
            resource_type="issue",
            resource_id=issue.id,
            description=f"Resolved issue '{issue.title}'",
        )
    elif issue_data.status in {"open", "in_progress"}:
        issue.resolved_at = None

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=issue.project_id,
        action="updated",
        resource_type="issue",
        resource_id=issue.id,
        description=f"Updated issue '{issue.title}'",
    )
    database_session.commit()
    database_session.refresh(issue)
    return issue

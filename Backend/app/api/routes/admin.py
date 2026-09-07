import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.routes.audit_logs import build_audit_log_query, serialize_audit_logs
from app.core.permissions import AdminUser
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.issue import Issue
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.user import User
from app.models.verification_run import VerificationRun
from app.schemas.admin import (
    AdminIssueResponse,
    AdminProjectOwner,
    AdminProjectResponse,
    AdminStatisticsResponse,
    AdminTeamResponse,
    AdminUserResponse,
    AdminVerificationRunResponse,
)
from app.services.report_service import build_admin_statistics

router = APIRouter(prefix="/admin")


@router.get("/statistics", response_model=AdminStatisticsResponse)
def admin_statistics(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    return build_admin_statistics(database_session)


@router.get("/users", response_model=list[AdminUserResponse])
def admin_list_users(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    users = database_session.scalars(
        select(User).order_by(User.created_at.desc())
    ).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.system_role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.get("/projects", response_model=list[AdminProjectResponse])
def admin_list_projects(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    projects = database_session.scalars(
        select(Project)
        .options(selectinload(Project.owner))
        .order_by(Project.created_at.desc())
    ).all()
    results: list[dict] = []
    for project in projects:
        suite_ids = select(TestSuite.id).where(
            TestSuite.project_id == project.id
        )
        member_count = (
            database_session.scalar(
                select(func.count(ProjectMember.id)).where(
                    ProjectMember.project_id == project.id
                )
            )
            or 0
        )
        test_suite_count = (
            database_session.scalar(
                select(func.count(TestSuite.id)).where(
                    TestSuite.project_id == project.id
                )
            )
            or 0
        )
        test_case_count = (
            database_session.scalar(
                select(func.count(TestCase.id))
                .join(TestSuite)
                .where(TestSuite.project_id == project.id)
            )
            or 0
        )
        verification_run_count = (
            database_session.scalar(
                select(func.count(VerificationRun.id)).where(
                    VerificationRun.test_suite_id.in_(suite_ids)
                )
            )
            or 0
        )
        open_issue_count = (
            database_session.scalar(
                select(func.count(Issue.id)).where(
                    Issue.project_id == project.id,
                    Issue.status == "open",
                )
            )
            or 0
        )
        results.append(
            {
                "id": project.id,
                "name": project.name,
                "owner": AdminProjectOwner(
                    id=project.owner.id,
                    email=project.owner.email,
                    full_name=project.owner.full_name,
                ),
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "member_count": int(member_count) + 1,
                "test_suite_count": int(test_suite_count),
                "test_case_count": int(test_case_count),
                "verification_run_count": int(verification_run_count),
                "open_issue_count": int(open_issue_count),
            }
        )
    return results


@router.get("/teams", response_model=list[AdminTeamResponse])
def admin_list_teams(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    teams = database_session.scalars(
        select(Team).order_by(Team.created_at.desc())
    ).all()
    results: list[dict] = []
    for team in teams:
        member_count = (
            database_session.scalar(
                select(func.count(TeamMember.id)).where(
                    TeamMember.team_id == team.id
                )
            )
            or 0
        )
        results.append(
            {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "member_count": int(member_count),
                "created_at": team.created_at,
            }
        )
    return results


@router.get("/verification-runs", response_model=list[AdminVerificationRunResponse])
def admin_list_verification_runs(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    query = (
        select(VerificationRun)
        .join(TestSuite)
        .join(Project)
        .options(
            selectinload(VerificationRun.test_suite).selectinload(TestSuite.project)
        )
    )
    if project_id is not None:
        query = query.where(Project.id == project_id)
    if status is not None:
        query = query.where(VerificationRun.status == status)
    runs = database_session.scalars(
        query.order_by(VerificationRun.created_at.desc())
    ).all()
    return [
        {
            "id": run.id,
            "project_id": run.test_suite.project_id,
            "project_name": run.test_suite.project.name,
            "suite_id": run.test_suite_id,
            "suite_name": run.test_suite.name,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/issues", response_model=list[AdminIssueResponse])
def admin_list_issues(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    severity: str | None = Query(default=None),
) -> list[Issue]:
    query = select(Issue)
    if project_id is not None:
        query = query.where(Issue.project_id == project_id)
    if status is not None:
        query = query.where(Issue.status == status)
    if priority is not None:
        query = query.where(Issue.priority == priority)
    if severity is not None:
        query = query.where(Issue.severity == severity)
    return list(
        database_session.scalars(query.order_by(Issue.created_at.desc()))
    )


@router.get("/audit-logs")
def admin_list_audit_logs(
    _admin: AdminUser,
    database_session: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
):
    logs = database_session.scalars(
        build_audit_log_query(
            project_id=project_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
        ).order_by(AuditLog.created_at.desc())
    ).all()
    return serialize_audit_logs(logs)

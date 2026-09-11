import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.permissions import (
    MANAGE_PROJECT_ROLES,
    VIEW_PROJECT_ROLES,
    get_accessible_project,
    project_access_condition,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.test_suite import TestSuite
from app.models.user import User
from app.models.verification_run import VerificationRun
from app.schemas.project import (
    ProjectCreate,
    ProjectGitHubConfigResponse,
    ProjectGitHubConfigUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.verification import VerificationRunRead
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/projects")


def get_owned_project(
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
    allowed_roles: tuple[str, ...] | None = None,
) -> Project:
    user = database_session.get(User, owner_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return get_accessible_project(
        database_session,
        project_id,
        user,
        allowed_roles or VIEW_PROJECT_ROLES,
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    project = Project(
        owner_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        github_repo=project_data.github_repo.strip() if project_data.github_repo else None,
        github_default_branch=project_data.github_default_branch or "main",
        github_verification_enabled=project_data.github_verification_enabled,
        github_webhook_secret=project_data.github_webhook_secret,
    )
    database_session.add(project)
    database_session.flush()
    database_session.add(
        ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role="owner",
        )
    )
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project.id,
        action="created",
        resource_type="project",
        resource_id=project.id,
        description=f"Created project '{project.name}'",
    )
    database_session.commit()
    database_session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Project]:
    return list(
        database_session.scalars(
            select(Project)
            .where(project_access_condition(current_user.id))
            .order_by(Project.created_at.desc())
        )
    )


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    return get_owned_project(project_id, current_user.id, database_session)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    project = get_owned_project(
        project_id,
        current_user.id,
        database_session,
        MANAGE_PROJECT_ROLES,
    )

    for field, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project.id,
        action="updated",
        resource_type="project",
        resource_id=project.id,
        description=f"Updated project '{project.name}'",
    )
    database_session.commit()
    database_session.refresh(project)
    return project


def normalize_github_repo(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip()
    cleaned = re.sub(r"^https?://[^/]+/", "", cleaned)
    cleaned = re.sub(r"^git@[^:]+:", "", cleaned)
    cleaned = re.sub(r"\.git$", "", cleaned)
    return cleaned.strip("/")


def resolve_webhook_url(request: Request | None = None) -> str:
    if settings.webhook_base_url:
        return f"{settings.webhook_base_url.rstrip('/')}/api/v1/github/webhook"
    if request:
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if forwarded_host:
            proto = forwarded_proto or ("https" if "ngrok" in forwarded_host.lower() else request.url.scheme)
            return f"{proto}://{forwarded_host.rstrip('/')}/api/v1/github/webhook"
        return f"{str(request.base_url).rstrip('/')}/api/v1/github/webhook"
    return f"{settings.backend_url.rstrip('/')}/api/v1/github/webhook"


@router.get("/{project_id}/github", response_model=ProjectGitHubConfigResponse)
def get_project_github_config(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    request: Request,
) -> ProjectGitHubConfigResponse:
    project = get_owned_project(project_id, current_user.id, database_session)
    webhook_url = resolve_webhook_url(request)
    return ProjectGitHubConfigResponse(
        project_id=project.id,
        github_repo=project.github_repo,
        github_default_branch=project.github_default_branch or "main",
        github_verification_enabled=project.github_verification_enabled,
        is_connected=bool(project.github_repo),
        webhook_configured=bool(
            project.github_webhook_secret or settings.github_webhook_secret
        ),
        webhook_url=webhook_url,
    )


@router.patch("/{project_id}/github", response_model=ProjectGitHubConfigResponse)
def update_project_github_config(
    project_id: uuid.UUID,
    config_data: ProjectGitHubConfigUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    request: Request,
) -> ProjectGitHubConfigResponse:
    project = get_owned_project(
        project_id,
        current_user.id,
        database_session,
        MANAGE_PROJECT_ROLES,
    )

    if config_data.github_repo is not None:
        project.github_repo = normalize_github_repo(config_data.github_repo)
    if config_data.github_default_branch is not None:
        project.github_default_branch = config_data.github_default_branch.strip()
    if config_data.github_verification_enabled is not None:
        project.github_verification_enabled = config_data.github_verification_enabled
    if config_data.github_webhook_secret is not None:
        project.github_webhook_secret = (
            config_data.github_webhook_secret.strip()
            if config_data.github_webhook_secret.strip()
            else None
        )

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project.id,
        action="updated_github_config",
        resource_type="project",
        resource_id=project.id,
        description=f"Updated GitHub integration for '{project.name}' (repo: {project.github_repo or 'none'})",
    )
    database_session.commit()
    database_session.refresh(project)

    webhook_url = resolve_webhook_url(request)
    return ProjectGitHubConfigResponse(
        project_id=project.id,
        github_repo=project.github_repo,
        github_default_branch=project.github_default_branch or "main",
        github_verification_enabled=project.github_verification_enabled,
        is_connected=bool(project.github_repo),
        webhook_configured=bool(
            project.github_webhook_secret or settings.github_webhook_secret
        ),
        webhook_url=webhook_url,
    )


@router.get("/{project_id}/github/prs", response_model=list[VerificationRunRead])
def list_project_pr_verifications(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    limit: int = 50,
):
    project = get_owned_project(project_id, current_user.id, database_session)
    runs = list(
        database_session.scalars(
            select(VerificationRun)
            .join(TestSuite, VerificationRun.test_suite_id == TestSuite.id)
            .options(
                selectinload(VerificationRun.results),
                selectinload(VerificationRun.test_suite),
            )
            .where(
                TestSuite.project_id == project.id,
                or_(
                    VerificationRun.trigger_source == "github_pr",
                    VerificationRun.pr_number.is_not(None),
                ),
            )
            .order_by(VerificationRun.created_at.desc())
            .limit(limit)
        )
    )
    return runs

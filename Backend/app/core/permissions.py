"""Project and system permission helpers."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User

SYSTEM_ROLE_ADMIN = "admin"
SYSTEM_ROLE_USER = "user"

PROJECT_ROLE_OWNER = "owner"
PROJECT_ROLE_MANAGER = "manager"
PROJECT_ROLE_QA_LEAD = "qa_lead"
PROJECT_ROLE_TESTER = "tester"
PROJECT_ROLE_DEVELOPER = "developer"
PROJECT_ROLE_VIEWER = "viewer"

ALL_PROJECT_ROLES = (
    PROJECT_ROLE_OWNER,
    PROJECT_ROLE_MANAGER,
    PROJECT_ROLE_QA_LEAD,
    PROJECT_ROLE_TESTER,
    PROJECT_ROLE_DEVELOPER,
    PROJECT_ROLE_VIEWER,
)

# A single policy map keeps API authorization and the UI's published role matrix
# aligned.  Add a capability here before using it in a route.
ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    PROJECT_ROLE_OWNER: frozenset({"view", "execute_verification", "manage_test_assets", "manage_project", "manage_members"}),
    PROJECT_ROLE_MANAGER: frozenset({"view", "execute_verification", "manage_test_assets", "manage_project", "manage_members"}),
    PROJECT_ROLE_QA_LEAD: frozenset({"view", "execute_verification", "manage_test_assets"}),
    PROJECT_ROLE_TESTER: frozenset({"view", "execute_verification"}),
    PROJECT_ROLE_DEVELOPER: frozenset({"view"}),
    PROJECT_ROLE_VIEWER: frozenset({"view"}),
}


def roles_with(capability: str) -> tuple[str, ...]:
    return tuple(role for role in ALL_PROJECT_ROLES if capability in ROLE_CAPABILITIES[role])


VIEW_PROJECT_ROLES = roles_with("view")
EXECUTE_VERIFICATION_ROLES = roles_with("execute_verification")
MANAGE_TEST_ASSET_ROLES = roles_with("manage_test_assets")
MANAGE_PROJECT_ROLES = roles_with("manage_project")
MANAGE_MEMBER_ROLES = roles_with("manage_members")


def is_system_admin(user: User) -> bool:
    return (user.system_role or "").lower() == SYSTEM_ROLE_ADMIN


def user_project_ids_subquery(user_id: uuid.UUID):
    return select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)


def project_access_condition(user_id: uuid.UUID):
    return or_(
        Project.owner_id == user_id,
        Project.id.in_(user_project_ids_subquery(user_id)),
    )


def resolve_project_role(
    database_session: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str | None:
    project = database_session.get(Project, project_id)
    if project is None:
        return None
    if project.owner_id == user_id:
        return PROJECT_ROLE_OWNER
    membership = database_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if membership is None:
        return None
    return membership.role


def get_accessible_project(
    database_session: Session,
    project_id: uuid.UUID,
    user: User,
    allowed_roles: tuple[str, ...] | None = None,
) -> Project:
    if is_system_admin(user):
        project = database_session.get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    role = resolve_project_role(database_session, project_id, user.id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if allowed_roles is not None and role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient project permissions",
        )

    project = database_session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def require_admin() -> Callable[..., User]:
    def dependency(current_user: CurrentUser) -> User:
        if not is_system_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    return dependency


AdminUser = Annotated[User, Depends(require_admin())]


def require_project_role(
    allowed_roles: tuple[str, ...],
) -> Callable[..., Project]:
    def dependency(
        project_id: uuid.UUID,
        current_user: CurrentUser,
        database_session: Annotated[Session, Depends(get_db)],
    ) -> Project:
        return get_accessible_project(
            database_session,
            project_id,
            current_user,
            allowed_roles,
        )

    return dependency


def user_can_view_project(
    database_session: Session,
    project_id: uuid.UUID,
    user: User,
) -> bool:
    try:
        get_accessible_project(
            database_session,
            project_id,
            user,
            VIEW_PROJECT_ROLES,
        )
    except HTTPException:
        return False
    return True

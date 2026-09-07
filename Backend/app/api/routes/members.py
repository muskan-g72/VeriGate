import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.permissions import MANAGE_MEMBER_ROLES, get_accessible_project
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.member import (
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
)
from app.services.audit_service import record_audit_event

router = APIRouter()


@router.get(
    "/projects/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
def list_project_members(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[ProjectMember]:
    get_accessible_project(database_session, project_id, current_user)
    return list(
        database_session.scalars(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
    )


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_member(
    project_id: uuid.UUID,
    member_data: ProjectMemberCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> ProjectMember:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        MANAGE_MEMBER_ROLES,
    )
    if database_session.get(User, member_data.user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if member_data.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Owner role cannot be assigned directly",
        )
    member = ProjectMember(
        project_id=project_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )
    database_session.add(member)
    try:
        record_audit_event(
            database_session,
            user_id=current_user.id,
            project_id=project_id,
            action="assigned",
            resource_type="member",
            resource_id=member_data.user_id,
            description=f"Added project member with role '{member_data.role}'",
        )
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        ) from error
    database_session.refresh(member)
    return member


@router.patch(
    "/projects/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
)
def update_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    member_data: ProjectMemberUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> ProjectMember:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        MANAGE_MEMBER_ROLES,
    )
    if member_data.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Owner role cannot be assigned directly",
        )
    member = database_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )
    member.role = member_data.role
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project_id,
        action="updated",
        resource_type="member",
        resource_id=user_id,
        description=f"Updated project member role to '{member_data.role}'",
    )
    database_session.commit()
    database_session.refresh(member)
    return member


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    get_accessible_project(
        database_session,
        project_id,
        current_user,
        MANAGE_MEMBER_ROLES,
    )
    member = database_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project_id,
        action="deleted",
        resource_type="member",
        resource_id=user_id,
        description="Removed project member",
    )
    database_session.delete(member)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

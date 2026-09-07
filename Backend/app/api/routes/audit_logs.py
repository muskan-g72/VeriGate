import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.core.permissions import (
    AdminUser,
    is_system_admin,
    project_access_condition,
    user_project_ids_subquery,
)
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.schemas.audit_log import AuditLogResponse, AuditLogUserSummary

router = APIRouter(prefix="/audit-logs")


def build_audit_log_query(
    *,
    project_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
):
    query = select(AuditLog).options(selectinload(AuditLog.user))
    if project_id is not None:
        query = query.where(AuditLog.project_id == project_id)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    return query


def serialize_audit_log(log: AuditLog) -> dict:
    user_summary = None
    if log.user is not None:
        user_summary = AuditLogUserSummary(
            id=log.user.id,
            email=log.user.email,
            full_name=log.user.full_name,
        )
    return {
        "id": log.id,
        "user_id": log.user_id,
        "project_id": log.project_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "description": log.description,
        "created_at": log.created_at,
        "user": user_summary,
    }


def serialize_audit_logs(logs: list[AuditLog]) -> list[dict]:
    return [serialize_audit_log(log) for log in logs]


def user_visible_audit_filter(user_id: uuid.UUID):
    accessible_projects = select(Project.id).where(
        project_access_condition(user_id)
    )
    return or_(
        AuditLog.user_id == user_id,
        AuditLog.project_id.in_(accessible_projects),
    )


def get_audit_log_for_user(
    audit_log_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Session,
) -> AuditLog:
    log = database_session.scalar(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.id == audit_log_id)
    )
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    if is_system_admin(current_user):
        return log
    if log.user_id == current_user.id:
        return log
    if log.project_id is not None:
        accessible = database_session.scalar(
            select(Project.id).where(
                Project.id == log.project_id,
                project_access_condition(current_user.id),
            )
        )
        if accessible is not None:
            return log
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Audit log not found",
    )


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
) -> list[dict]:
    query = build_audit_log_query(
        project_id=project_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
    )
    if not is_system_admin(current_user):
        query = query.where(user_visible_audit_filter(current_user.id))
    logs = database_session.scalars(
        query.order_by(AuditLog.created_at.desc())
    ).all()
    return serialize_audit_logs(logs)


@router.get("/{audit_log_id}", response_model=AuditLogResponse)
def read_audit_log(
    audit_log_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    log = get_audit_log_for_user(audit_log_id, current_user, database_session)
    return serialize_audit_log(log)

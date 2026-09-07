"""Audit log recording service."""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    database_session: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    description: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        project_id=project_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
    )
    database_session.add(audit_log)
    return audit_log

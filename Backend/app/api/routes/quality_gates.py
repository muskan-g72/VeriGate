import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import CurrentUser
from app.api.routes.verification_runs import get_owned_verification_run
from app.core.permissions import MANAGE_TEST_ASSET_ROLES, VIEW_PROJECT_ROLES, get_accessible_project
from app.db.session import get_db
from app.models.quality_gate import QualityGate, QualityGateEvaluation
from app.schemas.quality_gate import QualityGateEvaluationRead, QualityGateRead, QualityGateUpdate
from app.services.audit_service import record_audit_event

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]

@router.get("/projects/{project_id}/quality-gate", response_model=QualityGateRead | None)
def get_quality_gate(project_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession):
    get_accessible_project(database_session, project_id, current_user, VIEW_PROJECT_ROLES)
    return database_session.scalar(select(QualityGate).where(QualityGate.project_id == project_id))

@router.put("/projects/{project_id}/quality-gate", response_model=QualityGateRead)
def put_quality_gate(project_id: uuid.UUID, payload: QualityGateUpdate, current_user: CurrentUser, database_session: DatabaseSession):
    get_accessible_project(database_session, project_id, current_user, MANAGE_TEST_ASSET_ROLES)
    gate = database_session.scalar(select(QualityGate).where(QualityGate.project_id == project_id))
    before = {key: getattr(gate, key) for key in payload.model_fields} if gate else None
    is_create = gate is None
    if gate is None:
        gate = QualityGate(project_id=project_id)
        database_session.add(gate)
    for key, value in payload.model_dump().items(): setattr(gate, key, value)
    gate.updated_by_id = current_user.id
    database_session.flush()
    record_audit_event(database_session, user_id=current_user.id, action="created" if is_create else "updated", resource_type="quality_gate", resource_id=gate.id, project_id=project_id, description=f"Quality gate changed: before={before}, after={payload.model_dump()}")
    database_session.commit(); database_session.refresh(gate)
    return gate

@router.get("/verification-runs/{verification_run_id}/quality-gate", response_model=QualityGateEvaluationRead | None)
def get_run_quality_gate(verification_run_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession):
    get_owned_verification_run(verification_run_id, current_user.id, database_session, VIEW_PROJECT_ROLES)
    return database_session.scalar(select(QualityGateEvaluation).where(QualityGateEvaluation.run_id == verification_run_id))

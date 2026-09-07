import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.verification_runs import get_owned_verification_result
from app.core.permissions import (
    EXECUTE_VERIFICATION_ROLES,
    VIEW_PROJECT_ROLES,
)
from app.db.session import get_db
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.audit_service import record_audit_event

router = APIRouter()


@router.post(
    "/verification-results/{verification_result_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    verification_result_id: uuid.UUID,
    evidence_data: EvidenceCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Evidence:
    verification_result = get_owned_verification_result(
        verification_result_id,
        current_user.id,
        database_session,
        EXECUTE_VERIFICATION_ROLES,
    )

    evidence = Evidence(
        verification_result_id=verification_result.id,
        type=evidence_data.type,
        name=evidence_data.name,
        description=evidence_data.description,
        content=evidence_data.content,
    )

    database_session.add(evidence)
    database_session.flush()

    project_id = verification_result.verification_run.test_suite.project_id

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project_id,
        action="created",
        resource_type="evidence",
        resource_id=evidence.id,
        description=f"Created evidence '{evidence.name}'",
    )

    database_session.commit()
    database_session.refresh(evidence)

    return evidence


@router.get(
    "/verification-results/{verification_result_id}/evidence",
    response_model=list[EvidenceResponse],
)
def list_evidence(
    verification_result_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Evidence]:
    verification_result = get_owned_verification_result(
        verification_result_id,
        current_user.id,
        database_session,
        VIEW_PROJECT_ROLES,
    )

    return list(
        database_session.scalars(
            select(Evidence)
            .where(
                Evidence.verification_result_id == verification_result.id
            )
            .order_by(Evidence.created_at.desc())
        )
    )


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceResponse,
)
def read_evidence(
    evidence_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Evidence:
    evidence = database_session.get(Evidence, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    get_owned_verification_result(
        evidence.verification_result_id,
        current_user.id,
        database_session,
        VIEW_PROJECT_ROLES,
    )

    return evidence


@router.delete(
    "/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evidence(
    evidence_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> None:
    evidence = database_session.get(Evidence, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    verification_result = get_owned_verification_result(
        evidence.verification_result_id,
        current_user.id,
        database_session,
        EXECUTE_VERIFICATION_ROLES,
    )

    project_id = verification_result.verification_run.test_suite.project_id

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project_id,
        action="deleted",
        resource_type="evidence",
        resource_id=evidence.id,
        description=f"Deleted evidence '{evidence.name}'",
    )

    database_session.delete(evidence)
    database_session.commit()
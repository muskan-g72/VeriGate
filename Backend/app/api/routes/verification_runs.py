import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.api.routes.test_suites import get_owned_test_suite
from app.core.permissions import (
    EXECUTE_VERIFICATION_ROLES,
    VIEW_PROJECT_ROLES,
)
from app.db.session import get_db
from app.models.test_case import TestCase
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.schemas.verification import (
    FINAL_RESULT_STATUSES,
    VerificationResultRead,
    VerificationResultUpdate,
    VerificationRunCreate,
    VerificationRunDetail,
    VerificationRunRead,
)
from app.services.audit_service import record_audit_event
from app.services.automated_verification import (
    execute_automated_results,
    sync_verification_run_status,
)

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_owned_verification_run(
    verification_run_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
    allowed_roles: tuple[str, ...] | None = None,
) -> VerificationRun:
    verification_run = database_session.scalar(
        select(VerificationRun)
        .options(
            selectinload(VerificationRun.test_suite),
            selectinload(VerificationRun.results).selectinload(
                VerificationResult.evidence_items
            ),
        )
        .where(VerificationRun.id == verification_run_id)
    )

    if verification_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification run not found",
        )

    if allowed_roles is None:
        allowed_roles = VIEW_PROJECT_ROLES

    get_owned_test_suite(
        test_suite_id=verification_run.test_suite_id,
        owner_id=owner_id,
        database_session=database_session,
        allowed_roles=allowed_roles,
    )

    return verification_run


def get_owned_verification_result(
    verification_result_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
    allowed_roles: tuple[str, ...] | None = None,
) -> VerificationResult:
    verification_result = database_session.scalar(
        select(VerificationResult)
        .options(
            selectinload(VerificationResult.evidence_items),
            selectinload(VerificationResult.test_case),
            selectinload(VerificationResult.verification_run).selectinload(
                VerificationRun.test_suite
            ),
        )
        .where(VerificationResult.id == verification_result_id)
    )

    if verification_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification result not found",
        )

    if allowed_roles is None:
        allowed_roles = VIEW_PROJECT_ROLES

    get_owned_test_suite(
        test_suite_id=verification_result.verification_run.test_suite_id,
        owner_id=owner_id,
        database_session=database_session,
        allowed_roles=allowed_roles,
    )

    return verification_result


def safe_record_audit_event(
    database_session: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    description: str | None = None,
) -> None:
    """
    Audit logging must never break verification execution.
    """
    try:
        record_audit_event(
            database_session,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            description=description,
        )
    except Exception:
        database_session.rollback()


@router.post(
    "/test-suites/{test_suite_id}/verification-runs",
    response_model=VerificationRunDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_run(
    test_suite_id: uuid.UUID,
    run_data: VerificationRunCreate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> VerificationRun:
    test_suite = get_owned_test_suite(
        test_suite_id=test_suite_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=EXECUTE_VERIFICATION_ROLES,
    )

    active_test_cases = list(
        database_session.scalars(
            select(TestCase)
            .where(
                TestCase.test_suite_id == test_suite.id,
                TestCase.is_active.is_(True),
            )
            .order_by(TestCase.created_at)
        )
    )

    if not active_test_cases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test suite has no active test cases",
        )

    verification_run = VerificationRun(
        test_suite_id=test_suite.id,
        created_by_id=current_user.id,
        name=run_data.name.strip(),
    )
    verification_run.results = [
        VerificationResult(test_case_id=test_case.id)
        for test_case in active_test_cases
    ]

    database_session.add(verification_run)
    database_session.flush()

    await execute_automated_results(
        database_session,
        verification_run=verification_run,
        test_cases=active_test_cases,
        user_id=current_user.id,
        project_id=test_suite.project_id,
    )

    safe_record_audit_event(
        database_session,
        user_id=current_user.id,
        action="executed",
        resource_type="verification_run",
        resource_id=verification_run.id,
        project_id=test_suite.project_id,
        description=f"Started verification run '{verification_run.name}'",
    )

    database_session.commit()
    database_session.refresh(verification_run)

    return get_owned_verification_run(
        verification_run_id=verification_run.id,
        owner_id=current_user.id,
        database_session=database_session,
    )


@router.get(
    "/test-suites/{test_suite_id}/verification-runs",
    response_model=list[VerificationRunRead],
)
def list_verification_runs(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> list[VerificationRun]:
    test_suite = get_owned_test_suite(
        test_suite_id=test_suite_id,
        owner_id=current_user.id,
        database_session=database_session,
    )
    return list(
        database_session.scalars(
            select(VerificationRun)
            .options(selectinload(VerificationRun.results))
            .where(VerificationRun.test_suite_id == test_suite.id)
            .order_by(VerificationRun.created_at.desc())
        )
    )


@router.get(
    "/verification-runs/{verification_run_id}",
    response_model=VerificationRunDetail,
)
def read_verification_run(
    verification_run_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> VerificationRun:
    return get_owned_verification_run(
        verification_run_id=verification_run_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=VIEW_PROJECT_ROLES,
    )


@router.get(
    "/verification-results/{verification_result_id}",
    response_model=VerificationResultRead,
)
def read_verification_result(
    verification_result_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> VerificationResult:
    return get_owned_verification_result(
        verification_result_id=verification_result_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=VIEW_PROJECT_ROLES,
    )


@router.patch(
    "/verification-results/{verification_result_id}",
    response_model=VerificationResultRead,
)
def update_verification_result(
    verification_result_id: uuid.UUID,
    result_data: VerificationResultUpdate,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> VerificationResult:
    verification_result = get_owned_verification_result(
        verification_result_id=verification_result_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=EXECUTE_VERIFICATION_ROLES,
    )

    previous_status = verification_result.status
    now = datetime.now(UTC)

    update_dict = result_data.model_dump(exclude_unset=True)
    for field in (
        "status",
        "actual_result",
        "notes",
        "failure_message",
        "stack_trace",
        "duration",
    ):
        if field in update_dict:
            setattr(verification_result, field, update_dict[field])

    if (
        result_data.status is not None
        and result_data.status in FINAL_RESULT_STATUSES
    ):
        verification_result.executed_at = now
    elif result_data.status in {"pending", "running"}:
        verification_result.executed_at = None

    verification_run = get_owned_verification_run(
        verification_run_id=verification_result.verification_run_id,
        owner_id=current_user.id,
        database_session=database_session,
    )
    sync_verification_run_status(verification_run, now)

    if (
        previous_status != verification_result.status
        and verification_result.status == "failed"
    ):
        safe_record_audit_event(
            database_session,
            user_id=current_user.id,
            action="failed",
            resource_type="verification_result",
            resource_id=verification_result.id,
            project_id=verification_run.test_suite.project_id,
            description="Verification result marked as failed",
        )
    else:
        audit_action = "failed" if verification_result.status == "failed" else "updated"
        safe_record_audit_event(
            database_session,
            user_id=current_user.id,
            action=audit_action,
            resource_type="verification_result",
            resource_id=verification_result.id,
            project_id=verification_run.test_suite.project_id,
            description=f"Updated verification result status to '{verification_result.status}'",
        )

    database_session.commit()
    database_session.refresh(verification_result)

    return verification_result
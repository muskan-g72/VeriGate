import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.api.routes.test_suites import get_owned_test_suite
from app.db.session import get_db
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.schemas.verification import (
    VerificationResultRead,
    VerificationResultUpdate,
    VerificationRunCreate,
    VerificationRunDetail,
    VerificationRunRead,
)

router = APIRouter()


def get_owned_verification_run(
    verification_run_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> VerificationRun:
    verification_run = database_session.scalar(
        select(VerificationRun)
        .join(TestSuite)
        .join(Project)
        .options(selectinload(VerificationRun.results))
        .where(
            VerificationRun.id == verification_run_id,
            Project.owner_id == owner_id,
        )
    )
    if verification_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification run not found",
        )
    return verification_run


def get_owned_verification_result(
    verification_result_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> VerificationResult:
    verification_result = database_session.scalar(
        select(VerificationResult)
        .join(VerificationRun)
        .join(TestSuite)
        .join(Project)
        .where(
            VerificationResult.id == verification_result_id,
            Project.owner_id == owner_id,
        )
    )
    if verification_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification result not found",
        )
    return verification_result


@router.post(
    "/test-suites/{test_suite_id}/verification-runs",
    response_model=VerificationRunDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_run(
    test_suite_id: uuid.UUID,
    run_data: VerificationRunCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> VerificationRun:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
    )
    active_test_cases = list(
        database_session.scalars(
            select(TestCase).where(
                TestCase.test_suite_id == test_suite.id,
                TestCase.is_active.is_(True),
            )
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
    database_session.commit()
    database_session.refresh(verification_run)
    return get_owned_verification_run(
        verification_run.id,
        current_user.id,
        database_session,
    )


@router.get(
    "/test-suites/{test_suite_id}/verification-runs",
    response_model=list[VerificationRunRead],
)
def list_verification_runs(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[VerificationRun]:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
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
    database_session: Annotated[Session, Depends(get_db)],
) -> VerificationRun:
    return get_owned_verification_run(
        verification_run_id,
        current_user.id,
        database_session,
    )


@router.patch(
    "/verification-results/{verification_result_id}",
    response_model=VerificationResultRead,
)
def update_verification_result(
    verification_result_id: uuid.UUID,
    result_data: VerificationResultUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> VerificationResult:
    verification_result = get_owned_verification_result(
        verification_result_id,
        current_user.id,
        database_session,
    )
    now = datetime.now(UTC)
    for field, value in result_data.model_dump(exclude_unset=True).items():
        setattr(verification_result, field, value)
    verification_result.executed_at = (
        None if result_data.status == "pending" else now
    )

    verification_run = get_owned_verification_run(
        verification_result.verification_run_id,
        current_user.id,
        database_session,
    )
    result_statuses = [
        result_data.status
        if result.id == verification_result.id
        else result.status
        for result in verification_run.results
    ]
    if all(result_status != "pending" for result_status in result_statuses):
        verification_run.status = "completed"
        verification_run.started_at = verification_run.started_at or now
        verification_run.completed_at = now
    elif any(result_status != "pending" for result_status in result_statuses):
        verification_run.status = "in_progress"
        verification_run.started_at = verification_run.started_at or now
        verification_run.completed_at = None
    else:
        verification_run.status = "pending"
        verification_run.started_at = None
        verification_run.completed_at = None

    database_session.commit()
    database_session.refresh(verification_result)
    return verification_result

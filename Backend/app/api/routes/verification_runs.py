import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.schemas.failure_analysis import (
    FailureAnalysis,
    VerificationRunAnalysisRequest,
    VerificationRunAnalysisResponse,
)
from app.schemas.verification import (
    FINAL_RESULT_STATUSES,
    VerificationResultRead,
    VerificationResultUpdate,
    VerificationRunCreate,
    ComparableRunRead,
    RunComparisonRead,
    VerificationRunDetail,
    VerificationRunRead,
)
from app.services.audit_service import record_audit_event
from app.services.automated_verification import (
    execute_automated_results,
    sync_verification_run_status,
)
from app.services.failure_analysis_service import (
    analyze_failed_result,
    analyze_verification_run,
)
from app.services.quality_gate_service import evaluate_completed_run
from app.services.report_generator import sanitize_report_text
from app.services.run_comparison_service import compare_run_results
from app.services.test_case_snapshot_service import build_test_case_snapshot, snapshot_value

router = APIRouter()

DatabaseSession = Annotated[Session, Depends(get_db)]


def safe_evaluate_completed_run(
    database_session: Session, verification_run: VerificationRun
) -> None:
    """A gate is advisory: evaluation failures must not interrupt a completed run."""
    try:
        # Keep evaluation writes in a savepoint so a bad gate cannot roll back the
        # run/result updates that caused completion.
        with database_session.begin_nested():
            evaluate_completed_run(database_session, verification_run)
    except Exception:
        pass


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
            selectinload(VerificationRun.results).selectinload(
                VerificationResult.test_case
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
        VerificationResult(
            test_case_id=test_case.id,
            test_case_snapshot=build_test_case_snapshot(test_case),
        )
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
    if verification_run.status == "completed":
        safe_evaluate_completed_run(database_session, verification_run)

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


def _comparison_run_summary(run: VerificationRun) -> dict:
    return {
        "id": run.id, "name": run.name, "status": run.status,
        "created_at": run.created_at, "completed_at": run.completed_at,
        "pr_number": run.pr_number, "pr_commit_sha": run.pr_commit_sha,
        "gate_outcome": run.quality_gate_evaluation.outcome if run.quality_gate_evaluation else None,
    }


@router.get("/test-suites/{test_suite_id}/comparable-runs", response_model=list[ComparableRunRead])
def list_comparable_runs(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    test_suite = get_owned_test_suite(test_suite_id, current_user.id, database_session)
    runs = database_session.scalars(
        select(VerificationRun)
        .options(selectinload(VerificationRun.results), selectinload(VerificationRun.quality_gate_evaluation))
        .where(VerificationRun.test_suite_id == test_suite.id, VerificationRun.status == "completed")
        .order_by(VerificationRun.created_at.desc()).limit(limit)
    )
    response = []
    for run in runs:
        executed = [result for result in run.results if result.status in FINAL_RESULT_STATUSES]
        pass_rate = round(100 * sum(result.status == "passed" for result in executed) / len(executed), 1) if executed else None
        response.append({"id": run.id, "label": run.name, "created_at": run.created_at, "status": run.status,
                         "pass_rate": pass_rate, "gate_outcome": run.quality_gate_evaluation.outcome if run.quality_gate_evaluation else None})
    return response


@router.get("/verification-runs/{target_run_id}/compare", response_model=RunComparisonRead)
def compare_verification_runs(
    target_run_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
    baseline_run_id: uuid.UUID | None = None,
) -> dict:
    target = database_session.scalar(select(VerificationRun).where(VerificationRun.id == target_run_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification run not found")
    get_owned_test_suite(target.test_suite_id, current_user.id, database_session, VIEW_PROJECT_ROLES)
    if baseline_run_id is None:
        baseline_run_id = database_session.scalar(
            select(VerificationRun.id).where(
                VerificationRun.test_suite_id == target.test_suite_id,
                VerificationRun.status == "completed",
                VerificationRun.created_at < target.created_at,
            ).order_by(VerificationRun.created_at.desc()).limit(1)
        )
        if baseline_run_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no earlier run to compare with")
    if baseline_run_id == target_run_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A run cannot be compared with itself")
    runs = list(database_session.scalars(
        select(VerificationRun).options(
            selectinload(VerificationRun.results).selectinload(VerificationResult.test_case),
            selectinload(VerificationRun.quality_gate_evaluation),
        ).where(VerificationRun.id.in_([baseline_run_id, target_run_id]))
    ))
    by_id = {run.id: run for run in runs}
    baseline, target = by_id.get(baseline_run_id), by_id.get(target_run_id)
    if baseline is None or target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification run not found")
    get_owned_test_suite(baseline.test_suite_id, current_user.id, database_session, VIEW_PROJECT_ROLES)
    if baseline.test_suite_id != target.test_suite_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Runs must belong to the same test suite and project")
    if baseline.status != "completed" or target.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run results are not final yet")
    if len(baseline.results) + len(target.results) > 6000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comparison is limited to 6,000 results")

    def serialize(results: list[VerificationResult]) -> list[dict]:
        return [{"id": item.id, "test_case_id": item.test_case_id, "status": item.status, "duration": item.duration,
                 "title": snapshot_value(item, "title"),
                 "priority": snapshot_value(item, "priority", "medium"),
                 "execution_mode": snapshot_value(item, "execution_mode", "manual"),
                 "failure_message": (sanitize_report_text(item.failure_message) or "")[:300] or None} for item in results]
    comparison = compare_run_results(serialize(baseline.results), serialize(target.results))
    baseline_gate = baseline.quality_gate_evaluation.outcome if baseline.quality_gate_evaluation else None
    target_gate = target.quality_gate_evaluation.outcome if target.quality_gate_evaluation else None
    return {"baseline": _comparison_run_summary(baseline), "target": _comparison_run_summary(target),
            **comparison, "gate_changed": baseline_gate != target_gate}


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
    if verification_run.status == "completed":
        safe_evaluate_completed_run(database_session, verification_run)

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


@router.post(
    "/verification-runs/{verification_run_id}/analyze",
    response_model=VerificationRunAnalysisResponse,
)
async def analyze_verification_run_endpoint(
    verification_run_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
    request_data: VerificationRunAnalysisRequest | None = None,
) -> VerificationRunAnalysisResponse:
    verification_run = get_owned_verification_run(
        verification_run_id=verification_run_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=VIEW_PROJECT_ROLES,
    )

    target_result_id = request_data.result_id if request_data else None
    analysis_response = await analyze_verification_run(
        verification_run,
        target_result_id=target_result_id,
    )

    safe_record_audit_event(
        database_session,
        user_id=current_user.id,
        action="analyzed",
        resource_type="verification_run",
        resource_id=verification_run.id,
        project_id=verification_run.test_suite.project_id,
        description=f"AI failure analysis run for '{verification_run.name}'",
    )

    return analysis_response


@router.post(
    "/verification-results/{verification_result_id}/analyze",
    response_model=FailureAnalysis,
)
async def analyze_verification_result_endpoint(
    verification_result_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
) -> FailureAnalysis:
    verification_result = get_owned_verification_result(
        verification_result_id=verification_result_id,
        owner_id=current_user.id,
        database_session=database_session,
        allowed_roles=VIEW_PROJECT_ROLES,
    )

    analysis = await analyze_failed_result(
        verification_result,
        verification_result.test_case,
    )
    return analysis

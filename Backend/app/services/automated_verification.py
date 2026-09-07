"""Apply Playwright execution to automated verification results."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.test_case import TestCase
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.schemas.verification import FINAL_RESULT_STATUSES
from app.services.audit_service import record_audit_event
from app.services.playwright_executor import execute_playwright_test


def sync_verification_run_status(
    verification_run: VerificationRun,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    result_statuses = [result.status for result in verification_run.results]
    if all(
        result_status in FINAL_RESULT_STATUSES for result_status in result_statuses
    ):
        verification_run.status = "completed"
        verification_run.started_at = verification_run.started_at or current_time
        verification_run.completed_at = current_time
    elif any(
        result_status in FINAL_RESULT_STATUSES or result_status == "running"
        for result_status in result_statuses
    ):
        verification_run.status = "in_progress"
        verification_run.started_at = verification_run.started_at or current_time
        verification_run.completed_at = None
    else:
        verification_run.status = "pending"
        verification_run.started_at = None
        verification_run.completed_at = None


def store_playwright_screenshot_evidence(
    database_session: Session,
    *,
    verification_result: VerificationResult,
    screenshot_content: str,
    user_id: UUID,
    project_id: UUID,
) -> Evidence:
    evidence = Evidence(
        type="screenshot",
        name="Playwright screenshot",
        description="Screenshot captured during automated Playwright execution",
        content=screenshot_content,
    )
    verification_result.evidence_items.append(evidence)
    database_session.flush()
    record_audit_event(
        database_session,
        user_id=user_id,
        project_id=project_id,
        action="created",
        resource_type="evidence",
        resource_id=evidence.id,
        description=f"Created evidence '{evidence.name}'",
    )
    return evidence


def apply_playwright_result(
    verification_result: VerificationResult,
    playwright_result: dict[str, Any],
    executed_at: datetime,
) -> None:
    result_status = playwright_result.get("status")
    verification_result.status = (
        result_status if result_status in {"passed", "failed"} else "failed"
    )
    verification_result.actual_result = playwright_result.get("actual_result")
    verification_result.failure_message = playwright_result.get("failure_message")
    verification_result.stack_trace = playwright_result.get("stack_trace")
    verification_result.duration = playwright_result.get("duration")
    verification_result.executed_at = executed_at


async def execute_automated_results(
    database_session: Session,
    *,
    verification_run: VerificationRun,
    test_cases: list[TestCase],
    user_id: UUID,
    project_id: UUID,
) -> None:
    test_cases_by_id = {test_case.id: test_case for test_case in test_cases}
    now = datetime.now(UTC)
    executed_any = False

    for result in verification_run.results:
        test_case = test_cases_by_id.get(result.test_case_id)
        if test_case is None or test_case.execution_mode != "automated":
            continue

        steps = test_case.automation_steps or []
        if not isinstance(steps, list):
            steps = []

        try:
            playwright_result = await execute_playwright_test(steps)
        except Exception as exc:
            playwright_result = {
                "status": "failed",
                "actual_result": "Test failed",
                "failure_message": str(exc) or exc.__class__.__name__,
                "stack_trace": None,
                "duration": None,
                "screenshot": None,
            }

        apply_playwright_result(result, playwright_result, now)
        executed_any = True

        screenshot = playwright_result.get("screenshot")
        if screenshot:
            store_playwright_screenshot_evidence(
                database_session,
                verification_result=result,
                screenshot_content=screenshot,
                user_id=user_id,
                project_id=project_id,
            )

    if executed_any:
        sync_verification_run_status(verification_run, now)

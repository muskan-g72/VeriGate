import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.test_case import TestCase
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.services.audit_service import record_audit_event
from app.services.automated_verification import execute_automated_results
from app.services.failure_analysis_service import analyze_failed_result
from app.services.github_service import post_github_commit_status

logger = logging.getLogger(__name__)


async def run_github_pr_verification(
    verification_run_id: uuid.UUID,
    session: Session | None = None,
) -> None:
    """
    Background worker that executes automated verification tests for a GitHub PR-triggered run,
    collects screenshot evidence, runs AI failure diagnosis for defects, and publishes
    commit status back to GitHub.
    """
    owns_session = session is None
    database_session = session if session is not None else SessionLocal()
    try:
        verification_run = database_session.scalar(
            select(VerificationRun)
            .options(
                selectinload(VerificationRun.test_suite),
                selectinload(VerificationRun.results).selectinload(
                    VerificationResult.test_case
                ),
                selectinload(VerificationRun.results).selectinload(
                    VerificationResult.evidence_items
                ),
            )
            .where(VerificationRun.id == verification_run_id)
        )

        if not verification_run:
            logger.error(
                f"PR verification aborted: run {verification_run_id} not found."
            )
            return

        now = datetime.now(UTC)
        verification_run.status = "in_progress"
        verification_run.started_at = verification_run.started_at or now
        database_session.commit()

        suite = verification_run.test_suite
        project_id = suite.project_id if suite else None
        user_id = verification_run.created_by_id

        # Post initial pending status to GitHub
        if verification_run.pr_repository and verification_run.pr_commit_sha:
            target_url = f"{settings.frontend_url.rstrip('/')}/app/verification-runs/{verification_run.id}"
            await post_github_commit_status(
                repo=verification_run.pr_repository,
                commit_sha=verification_run.pr_commit_sha,
                state="pending",
                description="VeriGate automated verification running...",
                target_url=target_url,
            )

        # Retrieve active test cases
        active_test_cases = list(
            database_session.scalars(
                select(TestCase)
                .where(
                    TestCase.test_suite_id == verification_run.test_suite_id,
                    TestCase.is_active.is_(True),
                )
                .order_by(TestCase.created_at)
            )
        )

        # Execute automated test suite
        if active_test_cases and project_id:
            await execute_automated_results(
                database_session,
                verification_run=verification_run,
                test_cases=active_test_cases,
                user_id=user_id,
                project_id=project_id,
            )

        # Mark any remaining pending (e.g. manual) tests as skipped during CI/CD verification
        for result in verification_run.results:
            if result.status == "pending":
                result.status = "skipped"
                result.actual_result = (
                    "Manual test case skipped during automated PR verification."
                )
                result.executed_at = now

        # Run AI Failure Detective for any failed results
        for result in verification_run.results:
            if result.status in {"failed", "blocked"}:
                test_case = next(
                    (tc for tc in active_test_cases if tc.id == result.test_case_id),
                    result.test_case,
                )
                try:
                    analyze_failed_result(result, test_case)
                except Exception as exc:
                    logger.warning(
                        f"AI failure analysis skipped for result {result.id}: {exc}"
                    )

        # Mark run completed
        completion_time = datetime.now(UTC)
        verification_run.status = "completed"
        verification_run.completed_at = completion_time

        # Record audit log
        if project_id:
            try:
                record_audit_event(
                    database_session,
                    user_id=user_id,
                    action="verified_github_pr",
                    resource_type="verification_run",
                    resource_id=verification_run.id,
                    project_id=project_id,
                    description=f"GitHub PR #{verification_run.pr_number} verification completed: {verification_run.passed_count} passed, {verification_run.failed_count} failed",
                )
            except Exception:
                pass

        database_session.commit()

        # Publish final status to GitHub
        if verification_run.pr_repository and verification_run.pr_commit_sha:
            has_failures = (
                verification_run.failed_count > 0
                or verification_run.blocked_count > 0
            )
            state = "failure" if has_failures else "success"
            total = verification_run.total_cases
            passed = verification_run.passed_count
            failed = verification_run.failed_count
            desc = (
                f"VeriGate: {passed}/{total} tests passed"
                if not has_failures
                else f"VeriGate: {failed} failed of {total} tests"
            )
            target_url = f"{settings.frontend_url.rstrip('/')}/app/verification-runs/{verification_run.id}"

            await post_github_commit_status(
                repo=verification_run.pr_repository,
                commit_sha=verification_run.pr_commit_sha,
                state=state,
                description=desc,
                target_url=target_url,
            )

        logger.info(
            f"PR verification {verification_run.id} finished successfully: {verification_run.passed_count}/{verification_run.total_cases} passed."
        )

    except Exception as exc:
        logger.exception(f"Unhandled error during PR verification: {exc}")
        database_session.rollback()
    finally:
        if owns_session:
            database_session.close()

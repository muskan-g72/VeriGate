import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.test_case import TestCase
from app.models.project import Project
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.services.audit_service import record_audit_event
from app.services.automated_verification import execute_automated_results
from app.services.failure_analysis_service import analyze_failed_result
from app.services.github_service import post_github_commit_status
from app.services.github_pr_comment_service import publish_pr_comment
from app.services.quality_gate_service import evaluate_completed_run

logger = logging.getLogger(__name__)


async def publish_commit_status(
    database_session: Session,
    verification_run: VerificationRun,
    *,
    state: str,
    description: str,
    target_url: str,
    successful_status: str,
) -> None:
    """Publish and persist an outcome without interrupting comment publication."""
    try:
        result = await post_github_commit_status(
            repo=verification_run.pr_repository,
            commit_sha=verification_run.pr_commit_sha,
            state=state,
            description=description,
            target_url=target_url,
            return_details=True,
        )
        if isinstance(result, tuple):
            published, _status_code, error = result
        else:  # Preserve compatibility with mocked/legacy boolean callers.
            published, error = bool(result), "GitHub commit status could not be published"
    except Exception:
        published, error = False, "GitHub commit status request failed"

    verification_run.commit_status = successful_status if published else "failed"
    verification_run.commit_status_url = (
        f"https://github.com/{verification_run.pr_repository}/commit/"
        f"{verification_run.pr_commit_sha}"
        if published
        else None
    )
    verification_run.commit_status_error = None if published else error[:500]
    database_session.commit()


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
        project = database_session.get(Project, project_id) if project_id else None
        verification_run.comment_status = (
            "pending" if project and project.pr_comments_enabled else "disabled"
        )
        verification_run.commit_status = "pending"
        database_session.commit()

        # Post initial pending status to GitHub
        if verification_run.pr_repository and verification_run.pr_commit_sha:
            target_url = f"{settings.frontend_url.rstrip('/')}/app/verification-runs/{verification_run.id}"
            await publish_commit_status(
                database_session,
                verification_run,
                state="pending",
                description="VeriGate automated verification running...",
                target_url=target_url,
                successful_status="pending",
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
        automated_test_cases = [
            test_case
            for test_case in active_test_cases
            if test_case.execution_mode == "automated"
        ]

        if not automated_test_cases:
            verification_run.status = "completed"
            verification_run.completed_at = datetime.now(UTC)
            try:
                evaluate_completed_run(database_session, verification_run)
            except Exception:
                logger.exception("Quality gate evaluation failed for empty PR verification %s.", verification_run.id)
            if project_id:
                record_audit_event(
                    database_session,
                    user_id=user_id,
                    action="skipped_github_pr",
                    resource_type="verification_run",
                    resource_id=verification_run.id,
                    project_id=project_id,
                    description=(
                        f"GitHub PR #{verification_run.pr_number} verification skipped: "
                        "no active automated test suite configured for this project."
                    ),
                )
            database_session.commit()
            if verification_run.pr_repository and verification_run.pr_commit_sha:
                published = await post_github_commit_status(
                    repo=verification_run.pr_repository,
                    commit_sha=verification_run.pr_commit_sha,
                    state="error",
                    description=(
                        "VeriGate: no active automated test suite configured for this project"
                    ),
                    target_url=(
                        f"{settings.frontend_url.rstrip('/')}/app/test-library"
                        f"?projectId={project_id}"
                    ) if project_id else None,
                )
                if not published:
                    logger.warning(
                        "Unable to publish empty PR verification status for run %s.",
                        verification_run.id,
                    )
            return

        # Execute automated test suite
        if project_id:
            await execute_automated_results(
                database_session,
                verification_run=verification_run,
                test_cases=automated_test_cases,
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
        comment_analyses = {}
        analysis_deadline = asyncio.get_running_loop().time() + 20
        for result in verification_run.results:
            if result.status in {"failed", "blocked"}:
                test_case = next(
                    (tc for tc in automated_test_cases if tc.id == result.test_case_id),
                    result.test_case,
                )
                try:
                    if len(comment_analyses) < 3 and asyncio.get_running_loop().time() < analysis_deadline:
                        remaining = max(.1, analysis_deadline - asyncio.get_running_loop().time())
                        comment_analyses[str(result.id)] = await asyncio.wait_for(analyze_failed_result(result, test_case), timeout=remaining)
                except Exception as exc:
                    logger.warning(
                        f"AI failure analysis skipped for result {result.id}: {exc}"
                    )

        # Mark run completed
        completion_time = datetime.now(UTC)
        verification_run.status = "completed"
        verification_run.completed_at = completion_time

        try:
            gate_evaluation = evaluate_completed_run(database_session, verification_run)
        except Exception:
            logger.exception("Quality gate evaluation failed for PR verification %s.", verification_run.id)
            gate_evaluation = None

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
            has_executed_automated_result = any(
                result.status in {"passed", "failed", "blocked"}
                and result.test_case is not None
                and result.test_case.execution_mode == "automated"
                for result in verification_run.results
            )
            state = (
                "error"
                if not has_executed_automated_result
                else "failure" if has_failures else "success"
            )
            total = verification_run.total_cases
            passed = verification_run.passed_count
            failed = verification_run.failed_count
            desc = (
                "VeriGate: no automated tests were executed"
                if not has_executed_automated_result
                else f"VeriGate: {passed}/{total} tests passed"
                if not has_failures
                else f"VeriGate: {failed} failed of {total} tests"
            )
            if gate_evaluation and gate_evaluation.outcome in {"passed", "failed"}:
                state = "success" if gate_evaluation.outcome == "passed" else "failure"
                failed_rules = [rule["rule"] for rule in gate_evaluation.rule_results if not rule.get("passed")]
                desc = (
                    "VeriGate quality gate passed"
                    if gate_evaluation.outcome == "passed"
                    else f"VeriGate quality gate failed: {', '.join(failed_rules)}"
                )[:140]
            target_url = f"{settings.frontend_url.rstrip('/')}/app/verification-runs/{verification_run.id}"

            await publish_commit_status(
                database_session,
                verification_run,
                state=state,
                description=desc,
                target_url=target_url,
                successful_status="posted",
            )

        # A comment is an additive artifact; it is always attempted after the final
        # commit status and is not allowed to affect run completion.
        if project_id:
            if project:
                try:
                    await publish_pr_comment(database_session, verification_run, project, comment_analyses)
                except Exception:
                    database_session.rollback()
                    verification_run = database_session.get(VerificationRun, verification_run.id)
                    verification_run.comment_status = "failed"
                    verification_run.comment_error = "GitHub PR comment request failed"
                    database_session.commit()
                    logger.error("PR comment publication failed for run %s", verification_run.id)

        logger.info(
            f"PR verification {verification_run.id} finished successfully: {verification_run.passed_count}/{verification_run.total_cases} passed."
        )

    except Exception as exc:
        logger.exception(f"Unhandled error during PR verification: {exc}")
        database_session.rollback()
    finally:
        if owns_session:
            database_session.close()

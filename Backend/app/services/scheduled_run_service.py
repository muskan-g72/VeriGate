"""Database-backed interval scheduler for unattended automated verification."""
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.scheduled_run import ScheduledRun
from app.models.test_case import TestCase
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.services.audit_service import record_audit_event
from app.services.automated_verification import execute_automated_results, sync_verification_run_status
from app.services.quality_gate_service import evaluate_completed_run
from app.services.test_case_snapshot_service import build_test_case_snapshot


async def execute_scheduled_run(schedule_id) -> None:
    session = SessionLocal()
    try:
        schedule = session.get(ScheduledRun, schedule_id)
        if not schedule or not schedule.enabled:
            return
        cases = list(session.scalars(select(TestCase).where(TestCase.test_suite_id == schedule.test_suite_id, TestCase.is_active.is_(True))))
        now = datetime.now(UTC)
        run = VerificationRun(
            test_suite_id=schedule.test_suite_id, created_by_id=schedule.created_by_id,
            name=schedule.name, trigger_source="schedule", status="pending",
        )
        run.results = [VerificationResult(test_case_id=case.id, test_case_snapshot=build_test_case_snapshot(case)) for case in cases]
        session.add(run)
        session.flush()
        await execute_automated_results(session, verification_run=run, test_cases=cases, user_id=schedule.created_by_id, project_id=cases[0].test_suite.project_id if cases else None)
        for result in run.results:
            if result.status == "pending":
                result.status = "skipped"
                result.actual_result = "Manual test skipped during scheduled verification."
                result.executed_at = now
        sync_verification_run_status(run, now)
        if run.status == "completed":
            evaluate_completed_run(session, run)
        schedule.last_run_at = now
        schedule.last_run_id = run.id
        record_audit_event(session, user_id=schedule.created_by_id, project_id=cases[0].test_suite.project_id if cases else None, action="executed_scheduled_run", resource_type="verification_run", resource_id=run.id, description=f"Executed scheduled verification '{schedule.name}'")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def run_due_schedules() -> None:
    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        schedules = list(session.scalars(select(ScheduledRun).where(ScheduledRun.enabled.is_(True), ScheduledRun.next_run_at <= now)))
        for schedule in schedules:
            schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
        session.commit()
        for schedule in schedules:
            try:
                await execute_scheduled_run(schedule.id)
            except Exception:
                # One broken schedule must not prevent the remaining schedules
                # from being evaluated during this polling cycle.
                continue
    except Exception:
        # A fresh deployment may start before its migration has run; retry on
        # the next polling interval instead of preventing the API from serving.
        session.rollback()
    finally:
        session.close()


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await run_due_schedules()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
        except TimeoutError:
            pass

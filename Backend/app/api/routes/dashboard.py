import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.core.permissions import get_accessible_project, project_access_condition
from app.db.session import get_db
from app.models.issue import Issue
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun

router = APIRouter()


def _project_ids(database_session: Session, user_id: uuid.UUID):
    return select(Project.id).where(project_access_condition(user_id))


def _count(
    database_session: Session,
    statement,
) -> int:
    return int(database_session.scalar(statement) or 0)


@router.get("/dashboard/summary")
def dashboard_summary(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    project_ids = _project_ids(database_session, current_user.id)
    suite_ids = select(TestSuite.id).where(TestSuite.project_id.in_(project_ids))

    total_projects = _count(
        database_session,
        select(func.count(Project.id)).where(
            Project.id.in_(project_ids)
        ),
    )

    total_test_suites = _count(
        database_session,
        select(func.count(TestSuite.id)).where(
            TestSuite.project_id.in_(project_ids)
        ),
    )

    total_test_cases = _count(
        database_session,
        select(func.count(TestCase.id))
        .join(TestSuite)
        .where(TestSuite.project_id.in_(project_ids)),
    )

    total_verification_runs = _count(
        database_session,
        select(func.count(VerificationRun.id)).where(
            VerificationRun.test_suite_id.in_(suite_ids)
        ),
    )

    total_verification_results = _count(
        database_session,
        select(func.count(VerificationResult.id))
        .join(VerificationRun)
        .where(VerificationRun.test_suite_id.in_(suite_ids)),
    )

    passed_results = _count(
        database_session,
        select(func.count(VerificationResult.id))
        .join(VerificationRun)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "passed",
        ),
    )

    failed_results = _count(
        database_session,
        select(func.count(VerificationResult.id))
        .join(VerificationRun)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "failed",
        ),
    )

    blocked_results = _count(
        database_session,
        select(func.count(VerificationResult.id))
        .join(VerificationRun)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "blocked",
        ),
    )

    skipped_results = _count(
        database_session,
        select(func.count(VerificationResult.id))
        .join(VerificationRun)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "skipped",
        ),
    )

    open_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id.in_(project_ids),
            Issue.status == "open",
        ),
    )

    resolved_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id.in_(project_ids),
            Issue.status == "resolved",
        ),
    )

    recent_runs = database_session.scalars(
        select(VerificationRun)
        .join(TestSuite)
        .where(TestSuite.project_id.in_(project_ids))
        .options(selectinload(VerificationRun.results))
        .order_by(VerificationRun.created_at.desc())
        .limit(10)
    ).all()

    recent_run_data = []

    for run in recent_runs:
        total = run.total_cases
        passed = run.passed_count
        failed = run.failed_count
        blocked = run.blocked_count
        skipped = run.skipped_count

        completed_results = passed + failed + blocked + skipped
        pass_rate = (
            round((passed / completed_results) * 100, 2)
            if completed_results
            else 0.0
        )

        recent_run_data.append(
            {
                "run_id": run.id,
                "test_suite_id": run.test_suite_id,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "total": total,
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "skipped": skipped,
                "pending": run.pending_count,
                "pass_rate": pass_rate,
            }
        )

    pass_rate = (
        round((passed_results / total_verification_results) * 100, 2)
        if total_verification_results
        else 0.0
    )

    return {
        "total_projects": total_projects,
        "total_test_suites": total_test_suites,
        "total_test_cases": total_test_cases,
        "total_verification_runs": total_verification_runs,
        "total_verification_results": total_verification_results,
        "passed_results": passed_results,
        "failed_results": failed_results,
        "blocked_results": blocked_results,
        "skipped_results": skipped_results,
        "open_issues": open_issues,
        "resolved_issues": resolved_issues,
        "pass_rate": pass_rate,
        "recent_runs": recent_run_data,
    }


@router.get("/projects/{project_id}/summary")
def project_summary(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> dict:
    project = get_accessible_project(
        database_session,
        project_id,
        current_user,
    )

    suite_ids = select(TestSuite.id).where(
        TestSuite.project_id == project_id
    )

    total_suites = _count(
        database_session,
        select(func.count(TestSuite.id)).where(
            TestSuite.project_id == project_id
        ),
    )

    total_test_cases = _count(
        database_session,
        select(func.count(TestCase.id))
        .join(TestSuite)
        .where(TestSuite.project_id == project_id),
    )

    total_runs = _count(
        database_session,
        select(func.count(VerificationRun.id)).where(
            VerificationRun.test_suite_id.in_(suite_ids)
        ),
    )

    result_stats = database_session.execute(
        select(
            func.count(VerificationResult.id),
            func.sum(
                case(
                    (VerificationResult.status == "passed", 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (VerificationResult.status == "failed", 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (VerificationResult.status == "blocked", 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (VerificationResult.status == "skipped", 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (VerificationResult.status == "pending", 1),
                    else_=0,
                )
            ),
        )
        .join(VerificationRun)
        .where(VerificationRun.test_suite_id.in_(suite_ids))
    ).one()

    total_results = int(result_stats[0] or 0)
    passed = int(result_stats[1] or 0)
    failed = int(result_stats[2] or 0)
    blocked = int(result_stats[3] or 0)
    skipped = int(result_stats[4] or 0)
    pending = int(result_stats[5] or 0)

    open_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id == project_id,
            Issue.status == "open",
        ),
    )

    resolved_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id == project_id,
            Issue.status == "resolved",
        ),
    )

    latest_run = database_session.scalar(
        select(VerificationRun)
        .join(TestSuite)
        .where(TestSuite.project_id == project_id)
        .options(selectinload(VerificationRun.results))
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )

    latest_run_data = None

    if latest_run:
        completed_results = (
            latest_run.passed_count
            + latest_run.failed_count
            + latest_run.blocked_count
            + latest_run.skipped_count
        )

        latest_run_data = {
            "run_id": latest_run.id,
            "test_suite_id": latest_run.test_suite_id,
            "name": latest_run.name,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "completed_at": latest_run.completed_at,
            "total": latest_run.total_cases,
            "passed": latest_run.passed_count,
            "failed": latest_run.failed_count,
            "blocked": latest_run.blocked_count,
            "skipped": latest_run.skipped_count,
            "pending": latest_run.pending_count,
            "pass_rate": (
                round(
                    (latest_run.passed_count / completed_results) * 100,
                    2,
                )
                if completed_results
                else 0.0
            ),
        }

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
        "test_suites": total_suites,
        "test_cases": total_test_cases,
        "verification_runs": total_runs,
        "verification_results": {
            "total": total_results,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "skipped": skipped,
            "pending": pending,
            "pass_rate": (
                round((passed / total_results) * 100, 2)
                if total_results
                else 0.0
            ),
        },
        "issues": {
            "open": open_issues,
            "resolved": resolved_issues,
        },
        "latest_run": latest_run_data,
    }
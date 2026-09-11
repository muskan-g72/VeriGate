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
    project_id: uuid.UUID | None = None,
) -> dict:
    if project_id:
        get_accessible_project(database_session, project_id, current_user)
        target_project_ids = [project_id]
    else:
        target_project_ids = _project_ids(database_session, current_user.id)

    suite_ids = select(TestSuite.id).where(TestSuite.project_id.in_(target_project_ids))

    if project_id:
        total_projects = 1
    else:
        total_projects = _count(
            database_session,
            select(func.count(Project.id)).where(Project.id.in_(target_project_ids)),
        )

    total_test_suites = _count(
        database_session,
        select(func.count(TestSuite.id)).where(
            TestSuite.project_id.in_(target_project_ids)
        ),
    )

    total_test_cases = _count(
        database_session,
        select(func.count(TestCase.id))
        .join(TestSuite, TestSuite.id == TestCase.test_suite_id)
        .where(TestSuite.project_id.in_(target_project_ids)),
    )

    total_verification_runs = _count(
        database_session,
        select(func.count(VerificationRun.id)).where(
            VerificationRun.test_suite_id.in_(suite_ids)
        ),
    )

    completed_runs = _count(
        database_session,
        select(func.count(VerificationRun.id)).where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationRun.status == "completed",
        ),
    )

    running_runs = _count(
        database_session,
        select(func.count(VerificationRun.id)).where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationRun.status.in_(["in_progress", "pending"]),
        ),
    )

    failed_run_ids_subquery = (
        select(VerificationResult.verification_run_id)
        .join(
            VerificationRun,
            VerificationRun.id == VerificationResult.verification_run_id,
        )
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "failed",
        )
        .distinct()
    )
    failed_runs = _count(
        database_session,
        select(func.count()).select_from(failed_run_ids_subquery.subquery()),
    )
    passed_runs = max(0, completed_runs - failed_runs)

    result_stats = database_session.execute(
        select(
            func.count(VerificationResult.id),
            func.sum(case((VerificationResult.status == "passed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "failed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "blocked", 1), else_=0)),
            func.sum(case((VerificationResult.status == "skipped", 1), else_=0)),
            func.sum(case((VerificationResult.status == "pending", 1), else_=0)),
            func.avg(VerificationResult.duration),
        )
        .join(
            VerificationRun,
            VerificationRun.id == VerificationResult.verification_run_id,
        )
        .where(VerificationRun.test_suite_id.in_(suite_ids))
    ).one()

    total_verification_results = int(result_stats[0] or 0)
    passed_results = int(result_stats[1] or 0)
    failed_results = int(result_stats[2] or 0)
    blocked_results = int(result_stats[3] or 0)
    skipped_results = int(result_stats[4] or 0)
    pending_results = int(result_stats[5] or 0)
    avg_dur = result_stats[6]
    average_duration = round(float(avg_dur), 2) if avg_dur is not None else None

    completed_results = (
        passed_results + failed_results + blocked_results + skipped_results
    )
    pass_rate = (
        round((passed_results / completed_results) * 100, 1)
        if completed_results
        else None
    )
    failure_rate = (
        round((failed_results / completed_results) * 100, 1)
        if completed_results
        else None
    )

    open_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id.in_(target_project_ids),
            Issue.status.in_(["open", "in_progress"]),
        ),
    )

    resolved_issues = _count(
        database_session,
        select(func.count(Issue.id)).where(
            Issue.project_id.in_(target_project_ids),
            Issue.status.in_(["resolved", "closed"]),
        ),
    )

    # Deterministic Health Score Calculation
    recent_runs_for_score = database_session.scalars(
        select(VerificationRun)
        .where(VerificationRun.test_suite_id.in_(suite_ids))
        .options(selectinload(VerificationRun.results))
        .order_by(VerificationRun.created_at.desc())
        .limit(5)
    ).all()

    if completed_results == 0:
        health_score = None
        health_score_status = "unverified"
        health_score_explanation = "No verification runs have been executed yet."
        health_breakdown = {
            "pass_rate_points": 0.0,
            "reliability_points": 0.0,
            "defect_points": 0.0,
        }
    else:
        pass_rate_points = (passed_results / completed_results) * 60.0
        recent_failed_run_count = sum(
            1 for r in recent_runs_for_score if r.failed_count > 0
        )
        reliability_points = max(0.0, 25.0 - (recent_failed_run_count * 5.0))
        defect_points = max(0.0, 15.0 - (open_issues * 3.0))
        health_score = int(
            round(
                min(
                    100.0,
                    max(0.0, pass_rate_points + reliability_points + defect_points),
                )
            )
        )
        if health_score >= 85:
            health_score_status = "healthy"
        elif health_score >= 65:
            health_score_status = "degraded"
        else:
            health_score_status = "critical"

        health_score_explanation = (
            f"Health score is calculated from overall test pass rate ({round(pass_rate_points)}/60 pts), "
            f"recent run reliability ({round(reliability_points)}/25 pts), and open defect density ({round(defect_points)}/15 pts)."
        )
        health_breakdown = {
            "pass_rate_points": round(pass_rate_points, 1),
            "reliability_points": round(reliability_points, 1),
            "defect_points": round(defect_points, 1),
        }

    # Recent Verification Runs (limit 8)
    recent_runs_query = (
        select(
            VerificationRun,
            TestSuite.name.label("suite_name"),
            Project.name.label("project_name"),
        )
        .join(TestSuite, TestSuite.id == VerificationRun.test_suite_id)
        .join(Project, Project.id == TestSuite.project_id)
        .where(VerificationRun.test_suite_id.in_(suite_ids))
        .options(selectinload(VerificationRun.results))
        .order_by(VerificationRun.created_at.desc())
        .limit(8)
    )
    recent_runs_rows = database_session.execute(recent_runs_query).all()

    recent_run_data = []
    for run, suite_name, project_name in recent_runs_rows:
        total = run.total_cases
        passed = run.passed_count
        failed = run.failed_count
        blocked = run.blocked_count
        skipped = run.skipped_count
        pending = run.pending_count
        completed = passed + failed + blocked + skipped
        run_pass_rate = (
            round((passed / completed) * 100, 1) if completed else 0.0
        )

        result_durations = [
            r.duration for r in run.results if r.duration is not None
        ]
        if result_durations:
            run_duration = round(sum(result_durations), 2)
        elif run.started_at and run.completed_at:
            run_duration = round(
                (run.completed_at - run.started_at).total_seconds(), 2
            )
        else:
            run_duration = None

        recent_run_data.append(
            {
                "run_id": str(run.id),
                "id": str(run.id),
                "name": run.name,
                "test_suite_id": str(run.test_suite_id),
                "suite_name": suite_name,
                "project_name": project_name,
                "status": run.status,
                "duration": run_duration,
                "started_at": run.started_at.isoformat()
                if run.started_at
                else None,
                "completed_at": run.completed_at.isoformat()
                if run.completed_at
                else None,
                "created_at": run.created_at.isoformat()
                if run.created_at
                else None,
                "total": total,
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "skipped": skipped,
                "pending": pending,
                "pass_rate": run_pass_rate,
                "has_failures": failed > 0,
            }
        )

    # Recent Failures (limit 8)
    recent_failures_query = (
        select(
            VerificationResult,
            TestCase.title.label("test_case_title"),
            VerificationRun.name.label("run_name"),
            TestSuite.name.label("suite_name"),
            Project.name.label("project_name"),
        )
        .join(TestCase, TestCase.id == VerificationResult.test_case_id)
        .join(
            VerificationRun,
            VerificationRun.id == VerificationResult.verification_run_id,
        )
        .join(TestSuite, TestSuite.id == VerificationRun.test_suite_id)
        .join(Project, Project.id == TestSuite.project_id)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "failed",
        )
        .order_by(VerificationResult.created_at.desc())
        .limit(8)
    )
    recent_failures_rows = database_session.execute(recent_failures_query).all()

    recent_failures_data = []
    for (
        res,
        tc_title,
        run_name,
        suite_name,
        project_name,
    ) in recent_failures_rows:
        recent_failures_data.append(
            {
                "result_id": str(res.id),
                "run_id": str(res.verification_run_id),
                "run_name": run_name,
                "test_case_id": str(res.test_case_id),
                "test_case_title": tc_title,
                "suite_name": suite_name,
                "project_name": project_name,
                "status": res.status,
                "failure_message": res.failure_message
                or "Assertion or verification failure recorded.",
                "duration": res.duration,
                "executed_at": res.executed_at.isoformat()
                if res.executed_at
                else (res.created_at.isoformat() if res.created_at else None),
                "created_at": res.created_at.isoformat()
                if res.created_at
                else None,
            }
        )

    # Verification Trend Points (last 14 days)
    trend_rows = database_session.execute(
        select(
            func.date(VerificationRun.created_at).label("run_date"),
            func.count(func.distinct(VerificationRun.id)),
            func.sum(case((VerificationResult.status == "passed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "failed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "blocked", 1), else_=0)),
        )
        .join(
            VerificationResult,
            VerificationResult.verification_run_id == VerificationRun.id,
            isouter=True,
        )
        .where(VerificationRun.test_suite_id.in_(suite_ids))
        .group_by(func.date(VerificationRun.created_at))
        .order_by(func.date(VerificationRun.created_at).desc())
        .limit(14)
    ).all()

    trend_data = [
        {
            "date": str(row[0]),
            "runs": int(row[1] or 0),
            "passed": int(row[2] or 0),
            "failed": int(row[3] or 0),
            "blocked": int(row[4] or 0),
        }
        for row in reversed(trend_rows)
    ]

    return {
        "project_id": str(project_id) if project_id else None,
        "total_projects": total_projects,
        "total_test_suites": total_test_suites,
        "total_test_cases": total_test_cases,
        "total_runs": total_verification_runs,
        "total_verification_runs": total_verification_runs,
        "completed_runs": completed_runs,
        "running_runs": running_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "total_results": total_verification_results,
        "total_verification_results": total_verification_results,
        "passed_results": passed_results,
        "failed_results": failed_results,
        "blocked_results": blocked_results,
        "skipped_results": skipped_results,
        "pending_results": pending_results,
        "pass_rate": pass_rate if pass_rate is not None else 0.0,
        "failure_rate": failure_rate if failure_rate is not None else 0.0,
        "average_duration": average_duration,
        "open_issues": open_issues,
        "resolved_issues": resolved_issues,
        "health_score": health_score,
        "health_score_status": health_score_status,
        "health_score_explanation": health_score_explanation,
        "health_breakdown": health_breakdown,
        "recent_runs": recent_run_data,
        "recent_failures": recent_failures_data,
        "trend": trend_data,
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
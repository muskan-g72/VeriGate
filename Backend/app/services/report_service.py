"""Project reporting aggregates."""

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.issue import Issue
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun


def _project_suite_ids(database_session: Session, project_id: uuid.UUID):
    return select(TestSuite.id).where(TestSuite.project_id == project_id)


def build_project_report(database_session: Session, project_id: uuid.UUID) -> dict:
    suite_ids = _project_suite_ids(database_session, project_id)

    run_stats = database_session.execute(
        select(
            func.count(VerificationRun.id),
            func.sum(case((VerificationRun.status == "completed", 1), else_=0)),
            func.sum(case((VerificationRun.status == "in_progress", 1), else_=0)),
        ).where(VerificationRun.test_suite_id.in_(suite_ids))
    ).one()
    total_runs = int(run_stats[0] or 0)
    completed_runs = int(run_stats[1] or 0)
    in_progress_runs = int(run_stats[2] or 0)

    failed_runs = database_session.scalar(
        select(func.count(func.distinct(VerificationRun.id)))
        .join(VerificationResult)
        .where(
            VerificationRun.test_suite_id.in_(suite_ids),
            VerificationResult.status == "failed",
        )
    ) or 0

    result_stats = database_session.execute(
        select(
            func.count(VerificationResult.id),
            func.sum(case((VerificationResult.status == "passed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "failed", 1), else_=0)),
            func.sum(case((VerificationResult.status == "blocked", 1), else_=0)),
            func.sum(case((VerificationResult.status == "skipped", 1), else_=0)),
            func.sum(case((VerificationResult.status == "pending", 1), else_=0)),
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
    pass_rate = round((passed / total_results) * 100, 2) if total_results else 0.0

    issue_stats = database_session.execute(
        select(
            func.sum(case((Issue.status == "open", 1), else_=0)),
            func.sum(case((Issue.status == "in_progress", 1), else_=0)),
            func.sum(case((Issue.status == "resolved", 1), else_=0)),
            func.sum(case((Issue.status == "closed", 1), else_=0)),
        ).where(Issue.project_id == project_id)
    ).one()

    return {
        "verification": {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "in_progress_runs": in_progress_runs,
            "failed_runs": int(failed_runs),
        },
        "tests": {
            "total": total_results,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "skipped": skipped,
            "pending": pending,
            "pass_rate": pass_rate,
        },
        "issues": {
            "open": int(issue_stats[0] or 0),
            "in_progress": int(issue_stats[1] or 0),
            "resolved": int(issue_stats[2] or 0),
            "closed": int(issue_stats[3] or 0),
        },
    }


def build_verification_trend(
    database_session: Session,
    project_id: uuid.UUID,
) -> list[dict]:
    suite_ids = _project_suite_ids(database_session, project_id)
    rows = database_session.execute(
        select(
            func.date(VerificationRun.created_at).label("run_date"),
            func.count(VerificationRun.id),
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
        .order_by(func.date(VerificationRun.created_at))
    ).all()

    return [
        {
            "date": row.run_date.isoformat()
            if isinstance(row.run_date, date)
            else str(row.run_date),
            "runs": int(row[1] or 0),
            "passed": int(row[2] or 0),
            "failed": int(row[3] or 0),
            "blocked": int(row[4] or 0),
        }
        for row in rows
    ]


def build_issue_report(database_session: Session, project_id: uuid.UUID) -> dict:
    status_rows = database_session.execute(
        select(
            func.count(Issue.id),
            func.sum(case((Issue.status == "open", 1), else_=0)),
            func.sum(case((Issue.status == "in_progress", 1), else_=0)),
            func.sum(case((Issue.status == "resolved", 1), else_=0)),
            func.sum(case((Issue.status == "closed", 1), else_=0)),
        ).where(Issue.project_id == project_id)
    ).one()
    total = int(status_rows[0] or 0)

    priority_counts = {level: 0 for level in ("low", "medium", "high", "critical")}
    for priority, count in database_session.execute(
        select(Issue.priority, func.count(Issue.id))
        .where(Issue.project_id == project_id)
        .group_by(Issue.priority)
    ):
        if priority in priority_counts:
            priority_counts[priority] = int(count)

    severity_counts = {level: 0 for level in ("low", "medium", "high", "critical")}
    for severity, count in database_session.execute(
        select(Issue.severity, func.count(Issue.id))
        .where(Issue.project_id == project_id)
        .group_by(Issue.severity)
    ):
        if severity in severity_counts:
            severity_counts[severity] = int(count)

    return {
        "total": total,
        "open": int(status_rows[1] or 0),
        "in_progress": int(status_rows[2] or 0),
        "resolved": int(status_rows[3] or 0),
        "closed": int(status_rows[4] or 0),
        "by_priority": priority_counts,
        "by_severity": severity_counts,
    }


def build_admin_statistics(database_session: Session) -> dict:
    from app.models.project_member import ProjectMember
    from app.models.team import Team
    from app.models.user import User

    total_users = database_session.scalar(select(func.count(User.id))) or 0
    total_projects = database_session.scalar(select(func.count(Project.id))) or 0
    total_teams = database_session.scalar(select(func.count(Team.id))) or 0
    total_test_cases = (
        database_session.scalar(select(func.count(TestCase.id))) or 0
    )
    total_verification_runs = (
        database_session.scalar(select(func.count(VerificationRun.id))) or 0
    )
    total_issues = database_session.scalar(select(func.count(Issue.id))) or 0
    failed_results = database_session.scalar(
        select(func.count(VerificationResult.id)).where(
            VerificationResult.status == "failed"
        )
    ) or 0
    open_issues = database_session.scalar(
        select(func.count(Issue.id)).where(Issue.status == "open")
    ) or 0

    return {
        "total_users": int(total_users),
        "total_projects": int(total_projects),
        "total_teams": int(total_teams),
        "total_test_cases": int(total_test_cases),
        "total_verification_runs": int(total_verification_runs),
        "total_issues": int(total_issues),
        "failed_results": int(failed_results),
        "open_issues": int(open_issues),
    }

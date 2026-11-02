"""Bulk, read-only calculations used by the requirements traceability matrix."""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.issue import Issue
from app.models.requirement import Requirement
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun

UNRESOLVED_ISSUE_STATUSES = frozenset({"open", "in_progress"})


def build_traceability_matrix(
    database_session: Session,
    project_id: uuid.UUID,
    *,
    include_deprecated: bool = False,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    project_id = uuid.UUID(str(project_id))
    query = select(Requirement).where(Requirement.project_id == project_id)
    if not include_deprecated:
        query = query.where(Requirement.status != "deprecated")
    if status:
        query = query.where(Requirement.status == status)
    if priority:
        query = query.where(Requirement.priority == priority)
    if category:
        query = query.where(Requirement.category == category)
    total = database_session.scalar(select(func.count()).select_from(query.subquery())) or 0
    requirements = list(database_session.scalars(
        query.options(
            selectinload(Requirement.test_cases).selectinload(TestCase.test_suite),
            selectinload(Requirement.issues),
        ).order_by(Requirement.requirement_key).offset(offset).limit(limit)
    ))
    case_ids = {case.id for requirement in requirements for case in requirement.test_cases}
    latest_by_case = _latest_completed_results(database_session, project_id, case_ids)
    issues_by_case = _issues_by_test_case(database_session, project_id, case_ids)
    return {
        "items": [_trace_row(requirement, latest_by_case, issues_by_case) for requirement in requirements],
        "total": total,
    }


def _latest_completed_results(database_session: Session, project_id: uuid.UUID, case_ids: set[uuid.UUID]) -> dict:
    if not case_ids:
        return {}
    rank = func.row_number().over(
        partition_by=VerificationResult.test_case_id,
        order_by=(
            VerificationRun.completed_at.desc(),
            VerificationRun.created_at.desc(),
            VerificationResult.created_at.desc(),
        ),
    ).label("result_rank")
    ranked = select(
        VerificationResult.test_case_id.label("test_case_id"),
        VerificationResult.id.label("result_id"),
        VerificationResult.status.label("status"),
        VerificationRun.id.label("run_id"),
        VerificationRun.completed_at.label("completed_at"),
        rank,
    ).join(VerificationRun).join(TestSuite).where(
        TestSuite.project_id == project_id,
        VerificationRun.status == "completed",
        VerificationResult.test_case_id.in_(case_ids),
    ).subquery()
    return {
        row.test_case_id: row
        for row in database_session.execute(select(ranked).where(ranked.c.result_rank == 1)).all()
    }


def _issues_by_test_case(database_session: Session, project_id: uuid.UUID, case_ids: set[uuid.UUID]) -> dict:
    if not case_ids:
        return {}
    result: dict[uuid.UUID, list[Issue]] = defaultdict(list)
    for issue in database_session.scalars(select(Issue).where(Issue.project_id == project_id, Issue.test_case_id.in_(case_ids))):
        result[issue.test_case_id].append(issue)
    return result


def _trace_row(requirement: Requirement, latest_by_case: dict, issues_by_case: dict) -> dict:
    issue_by_id = {issue.id: issue for issue in requirement.issues}
    test_cases = []
    passed = 0
    failing = False
    for test_case in requirement.test_cases:
        latest = latest_by_case.get(test_case.id)
        latest_status = latest.status if latest else None
        passed += latest_status == "passed"
        failing = failing or latest_status in {"failed", "blocked"}
        for issue in issues_by_case.get(test_case.id, []):
            issue_by_id[issue.id] = issue
        test_cases.append({
            "id": test_case.id, "title": test_case.title, "test_suite_id": test_case.test_suite_id,
            "test_suite_name": test_case.test_suite.name, "priority": test_case.priority, "is_active": test_case.is_active,
            "latest_result_id": latest.result_id if latest else None, "latest_run_id": latest.run_id if latest else None,
            "latest_run_completed_at": latest.completed_at if latest else None, "latest_status": latest_status,
        })
    total = len(test_cases)
    not_passing = total - passed
    coverage_status = "untested" if not total else "passing" if passed == total else "failing" if failing else "not_passing"
    issues = [
        {"id": issue.id, "title": issue.title, "status": issue.status, "severity": issue.severity, "priority": issue.priority}
        for issue in sorted(issue_by_id.values(), key=lambda item: item.created_at, reverse=True)
    ]
    return {
        "id": requirement.id, "project_id": requirement.project_id, "requirement_key": requirement.requirement_key,
        "title": requirement.title, "description": requirement.description, "priority": requirement.priority,
        "category": requirement.category, "status": requirement.status, "source": requirement.source,
        "created_by_id": requirement.created_by_id, "created_at": requirement.created_at, "updated_at": requirement.updated_at,
        "coverage_status": coverage_status, "linked_test_case_count": total, "passing_test_case_count": passed,
        "not_passing_test_case_count": not_passing,
        "unresolved_issue_count": sum(issue.status in UNRESOLVED_ISSUE_STATUSES for issue in issue_by_id.values()),
        "test_cases": test_cases, "issues": issues,
    }

"""Detect test cases whose recent completed results alternate between pass and fail."""
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun

OUTCOME_MAP = {"passed": "passed", "failed": "failed", "blocked": "failed"}
RECENT_EXECUTIONS = 10
MIN_EXECUTIONS = 3


def summarize_history(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return a flaky summary for chronological executable outcomes, or None when stable."""
    if len(items) < MIN_EXECUTIONS:
        return None
    outcomes = [item["outcome"] for item in items]
    flips = sum(left != right for left, right in zip(outcomes, outcomes[1:]))
    if not flips or len(set(outcomes)) < 2:
        return None
    return {
        "executions": len(items),
        "passed": outcomes.count("passed"),
        "failed": outcomes.count("failed"),
        "flips": flips,
        "stability_score": round(100 * (1 - flips / (len(outcomes) - 1)), 1),
        "latest_status": items[-1]["status"],
        "history": [
            {"status": item["status"], "completed_at": item["completed_at"]}
            for item in reversed(items)
        ],
    }


def list_flaky_tests(database_session: Session, project_id, limit: int = 50) -> list[dict[str, Any]]:
    rows = database_session.execute(
        select(VerificationResult, TestCase, TestSuite, VerificationRun)
        .join(TestCase, TestCase.id == VerificationResult.test_case_id)
        .join(TestSuite, TestSuite.id == TestCase.test_suite_id)
        .join(VerificationRun, VerificationRun.id == VerificationResult.verification_run_id)
        .where(
            TestSuite.project_id == project_id,
            VerificationRun.status == "completed",
            VerificationResult.status.in_(tuple(OUTCOME_MAP)),
        )
        .order_by(VerificationResult.test_case_id, VerificationRun.completed_at.asc(), VerificationResult.created_at.asc())
    ).all()

    histories: dict = defaultdict(list)
    metadata: dict = {}
    for result, test_case, suite, run in rows:
        histories[test_case.id].append({
            "outcome": OUTCOME_MAP[result.status],
            "status": result.status,
            "completed_at": run.completed_at,
        })
        metadata[test_case.id] = {
            "test_case_id": test_case.id,
            "test_case_title": test_case.title,
            "test_suite_id": suite.id,
            "test_suite_name": suite.name,
        }

    detected = []
    for test_case_id, history in histories.items():
        summary = summarize_history(history[-RECENT_EXECUTIONS:])
        if summary:
            detected.append({**metadata[test_case_id], **summary})
    return sorted(detected, key=lambda item: (item["stability_score"], -item["flips"]))[:limit]

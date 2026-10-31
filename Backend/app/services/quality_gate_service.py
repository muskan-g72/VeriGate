"""Quality gate evaluation with deterministic, testable rule functions."""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.issue import Issue
from app.models.quality_gate import QualityGate, QualityGateEvaluation
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun


def gate_snapshot(gate: QualityGate) -> dict[str, Any]:
    return {key: getattr(gate, key) for key in (
        "enabled", "min_pass_rate_enabled", "min_pass_rate", "critical_tests_enabled",
        "critical_priorities", "critical_issues_enabled", "min_executed_tests_enabled",
        "min_executed_tests", "treat_blocked_as_failure",
    )}


def evaluate_rules(gate: QualityGate, results: list, open_critical_issues: int) -> tuple[str, list[dict[str, Any]]]:
    snapshot = gate_snapshot(gate)
    if not gate.enabled or not any((gate.min_pass_rate_enabled, gate.critical_tests_enabled, gate.critical_issues_enabled, gate.min_executed_tests_enabled)):
        return "not_configured", []
    executed = [r for r in results if r.status not in {"pending", "running", "skipped"}]
    passed = sum(r.status == "passed" for r in executed)
    failures = {"failed", "blocked"} if gate.treat_blocked_as_failure else {"failed"}
    checks: list[dict[str, Any]] = []
    if gate.min_pass_rate_enabled:
        rate = round(100 * passed / len(executed), 2) if executed else 0.0
        ok = rate >= (gate.min_pass_rate or 0)
        checks.append({"rule": "min_pass_rate", "measured_value": rate, "threshold": gate.min_pass_rate, "passed": ok, "reason": f"Pass rate {rate}% {'meets' if ok else 'is below'} {gate.min_pass_rate}%"})
    if gate.critical_tests_enabled:
        critical = [r for r in results if getattr(r.test_case, "priority", None) in (gate.critical_priorities or ["critical"]) and r.status in failures]
        ok = not critical
        checks.append({"rule": "no_failed_critical_tests", "measured_value": len(critical), "threshold": 0, "passed": ok, "reason": "No configured-priority test failed or blocked" if ok else f"{len(critical)} configured-priority test(s) failed or blocked"})
    if gate.critical_issues_enabled:
        ok = open_critical_issues == 0
        checks.append({"rule": "no_open_critical_issues", "measured_value": open_critical_issues, "threshold": 0, "passed": ok, "reason": "No open critical issues" if ok else f"{open_critical_issues} open critical issue(s)"})
    if gate.min_executed_tests_enabled:
        ok = len(executed) >= gate.min_executed_tests
        checks.append({"rule": "min_executed_tests", "measured_value": len(executed), "threshold": gate.min_executed_tests, "passed": ok, "reason": f"{len(executed)} executed test(s) {'meets' if ok else 'is below'} {gate.min_executed_tests}"})
    return ("passed" if all(check["passed"] for check in checks) else "failed"), checks


def evaluate_completed_run(database_session: Session, verification_run: VerificationRun) -> QualityGateEvaluation:
    """Replace a run evaluation; callers commit as part of their completion transaction."""
    run = database_session.scalar(select(VerificationRun).options(selectinload(VerificationRun.results).selectinload(VerificationResult.test_case), selectinload(VerificationRun.test_suite)).where(VerificationRun.id == verification_run.id)) or verification_run
    project_id = run.test_suite.project_id
    gate = database_session.scalar(select(QualityGate).where(QualityGate.project_id == project_id))
    evaluation = database_session.scalar(select(QualityGateEvaluation).where(QualityGateEvaluation.run_id == run.id))
    if evaluation is None:
        evaluation = QualityGateEvaluation(run_id=run.id)
        database_session.add(evaluation)
    evaluation.gate_id = gate.id if gate else None
    evaluation.evaluated_at = datetime.now(UTC)
    if not gate:
        evaluation.outcome, evaluation.rules_snapshot, evaluation.rule_results = "not_configured", {}, []
        return evaluation
    open_critical = len(list(database_session.scalars(select(Issue.id).where(Issue.project_id == project_id, Issue.severity == "critical", Issue.status.in_(("open", "in_progress"))))))
    evaluation.outcome, evaluation.rule_results = evaluate_rules(gate, run.results, open_critical)
    evaluation.rules_snapshot = gate_snapshot(gate)
    return evaluation

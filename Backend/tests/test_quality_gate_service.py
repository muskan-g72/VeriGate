from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.quality_gate import QualityGate
from app.schemas.quality_gate import QualityGateUpdate
from app.services.quality_gate_service import evaluate_rules


def gate(**updates):
    values = dict(enabled=True, min_pass_rate_enabled=False, min_pass_rate=None,
                  critical_tests_enabled=False, critical_priorities=["critical"],
                  critical_issues_enabled=False, min_executed_tests_enabled=False,
                  min_executed_tests=1, treat_blocked_as_failure=True)
    values.update(updates)
    return QualityGate(**values)


def result(status, priority="medium"):
    return SimpleNamespace(status=status, test_case=SimpleNamespace(priority=priority))


def test_pass_rate_boundary_and_empty_execution():
    configured = gate(min_pass_rate_enabled=True, min_pass_rate=50)
    assert evaluate_rules(configured, [result("passed"), result("failed")], 0)[0] == "passed"
    assert evaluate_rules(configured, [result("failed")], 0)[0] == "failed"


def test_blocked_handling_and_priority_aware_critical_rule():
    critical = gate(critical_tests_enabled=True)
    assert evaluate_rules(critical, [result("blocked", "critical")], 0)[0] == "failed"
    assert evaluate_rules(gate(critical_tests_enabled=True, treat_blocked_as_failure=False), [result("blocked", "critical")], 0)[0] == "passed"
    assert evaluate_rules(critical, [result("failed", "high")], 0)[0] == "passed"


def test_minimum_execution_open_issues_and_all_disabled():
    assert evaluate_rules(gate(min_executed_tests_enabled=True, min_executed_tests=1), [], 0)[0] == "failed"
    assert evaluate_rules(gate(critical_issues_enabled=True), [result("passed")], 1)[0] == "failed"
    assert evaluate_rules(gate(), [result("failed")], 5) == ("not_configured", [])


@pytest.mark.parametrize("payload", [
    {"min_pass_rate_enabled": True, "min_pass_rate": -0.01},
    {"min_pass_rate_enabled": True, "min_pass_rate": 100.01},
    {"min_executed_tests_enabled": True, "min_executed_tests": -1},
    {"min_executed_tests_enabled": True, "min_executed_tests": 1.5},
])
def test_quality_gate_threshold_validation_rejects_invalid_values(payload):
    with pytest.raises(ValidationError):
        QualityGateUpdate(**payload)

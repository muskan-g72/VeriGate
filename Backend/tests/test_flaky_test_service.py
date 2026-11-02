from app.services.flaky_test_service import summarize_history


def history(*outcomes):
    return [{"outcome": outcome, "status": outcome, "completed_at": None} for outcome in outcomes]


def test_detects_pass_fail_flips_and_stability_score():
    summary = summarize_history(history("passed", "failed", "passed", "failed"))
    assert summary["flips"] == 3
    assert summary["stability_score"] == 0.0
    assert summary["passed"] == 2 and summary["failed"] == 2


def test_does_not_flag_consistent_or_insufficient_history():
    assert summarize_history(history("passed", "passed", "passed")) is None
    assert summarize_history(history("passed", "failed")) is None

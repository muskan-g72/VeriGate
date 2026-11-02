from types import SimpleNamespace

from app.services.test_case_snapshot_service import build_test_case_snapshot, snapshot_value


def test_snapshot_is_immutable_after_test_case_changes():
    test_case = SimpleNamespace(
        title="Original title", description="Original description", steps="Step one",
        expected_result="Works", priority="high", is_active=True,
        execution_mode="manual", automation_steps=None,
    )
    snapshot = build_test_case_snapshot(test_case)
    test_case.title = "Renamed later"
    result = SimpleNamespace(test_case_snapshot=snapshot, test_case=test_case)
    assert snapshot_value(result, "title") == "Original title"
    assert snapshot_value(result, "priority") == "high"


def test_old_results_fall_back_to_live_test_case_definition():
    result = SimpleNamespace(test_case_snapshot=None, test_case=SimpleNamespace(title="Legacy title"))
    assert snapshot_value(result, "title") == "Legacy title"

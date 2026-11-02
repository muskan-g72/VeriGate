from app.services.run_comparison_service import compare_run_results


def test_comparison_classifies_changes_and_duration_flags() -> None:
    baseline = [
        {"id": "before-1", "test_case_id": "one", "status": "passed", "duration": 2, "title": "Login", "priority": "high", "execution_mode": "manual"},
        {"id": "before-2", "test_case_id": "two", "status": "failed", "duration": 5, "title": "Export", "priority": "medium", "execution_mode": "automated"},
        {"id": "before-3", "test_case_id": "three", "status": "skipped", "duration": None, "title": "Legacy", "priority": "low", "execution_mode": "manual"},
    ]
    target = [
        {"id": "after-1", "test_case_id": "one", "status": "failed", "duration": 4.5, "title": "Login", "priority": "high", "execution_mode": "manual"},
        {"id": "after-2", "test_case_id": "two", "status": "passed", "duration": 2, "title": "Export", "priority": "medium", "execution_mode": "automated"},
        {"id": "after-4", "test_case_id": "four", "status": "passed", "duration": 1, "title": "New case", "priority": "critical", "execution_mode": "manual"},
    ]

    comparison = compare_run_results(baseline, target)

    assert [row["category"] for row in comparison["rows"]] == ["regressed", "added", "removed", "improved"]
    regression = comparison["rows"][0]
    assert regression["slower"] is True
    assert regression["duration_absolute_delta"] == 2.5
    assert comparison["summary"]["counts"] == {"regressed": 1, "changed_other": 0, "added": 1, "removed": 1, "improved": 1, "unchanged": 0}


def test_comparison_handles_final_statuses_null_durations_and_strict_thresholds() -> None:
    baseline = [
        {"id": "one-before", "test_case_id": "one", "status": "blocked", "duration": 2, "title": "Blocked", "priority": "medium"},
        {"id": "two-before", "test_case_id": "two", "status": "skipped", "duration": None, "title": "Skipped", "priority": "medium"},
        {"id": "three-before", "test_case_id": "three", "status": "passed", "duration": 2, "title": "Boundary", "priority": "medium"},
        {"id": "four-before", "test_case_id": "four", "status": "pending", "duration": 2, "title": "Pending", "priority": "medium"},
    ]
    target = [
        {"id": "one-after", "test_case_id": "one", "status": "passed", "duration": 0.5, "title": "Blocked", "priority": "medium"},
        {"id": "two-after", "test_case_id": "two", "status": "pending", "duration": 1, "title": "Skipped", "priority": "medium"},
        {"id": "three-after", "test_case_id": "three", "status": "passed", "duration": 3, "title": "Boundary", "priority": "medium"},
        {"id": "four-after", "test_case_id": "four", "status": "skipped", "duration": None, "title": "Pending", "priority": "medium"},
    ]

    comparison = compare_run_results(baseline, target)
    rows = {row["test_case_id"]: row for row in comparison["rows"]}

    assert rows["one"]["category"] == "improved"
    assert rows["two"]["category"] == "changed_other"
    assert rows["two"]["duration_delta"] is None
    assert rows["three"]["duration_percent_delta"] == 50.0
    assert rows["three"]["slower"] is False
    assert rows["four"]["category"] == "changed_other"
    assert comparison["summary"]["baseline_pass_rate"] == 33.3
    assert comparison["summary"]["target_pass_rate"] == 66.7
    assert comparison["summary"]["pass_rate_delta"] == 33.4

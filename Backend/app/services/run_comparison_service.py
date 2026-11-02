"""Pure comparison logic for completed verification runs."""

from __future__ import annotations

from typing import Any

SLOWER_PERCENT_THRESHOLD = 50.0
SLOWER_SECONDS_THRESHOLD = 1.0
_CATEGORY_ORDER = {"regressed": 0, "changed_other": 1, "added": 2, "removed": 3, "improved": 4, "unchanged": 5}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_FINAL_STATUSES = {"passed", "failed", "blocked", "skipped"}


def _duration(value: Any) -> float | None:
    return float(value) if value is not None else None


def _pass_rate(results: list[dict[str, Any]]) -> float | None:
    executed = [item for item in results if item.get("status") in _FINAL_STATUSES]
    return round(100 * sum(item.get("status") == "passed" for item in executed) / len(executed), 1) if executed else None


def _category(before: str | None, after: str | None) -> str:
    if before is None:
        return "added"
    if after is None:
        return "removed"
    if before == "passed" and after in {"failed", "blocked"}:
        return "regressed"
    if before in {"failed", "blocked"} and after == "passed":
        return "improved"
    return "unchanged" if before == after else "changed_other"


def compare_run_results(
    baseline_results: list[dict[str, Any]], target_results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare plain result mappings; this deliberately has no database dependency."""
    baseline_by_case = {str(item["test_case_id"]): item for item in baseline_results}
    target_by_case = {str(item["test_case_id"]): item for item in target_results}
    rows: list[dict[str, Any]] = []
    counts = {key: 0 for key in _CATEGORY_ORDER}
    slower_count = faster_count = 0

    for case_id in baseline_by_case.keys() | target_by_case.keys():
        before, after = baseline_by_case.get(case_id), target_by_case.get(case_id)
        source = after or before or {}
        before_duration = _duration(before.get("duration")) if before else None
        after_duration = _duration(after.get("duration")) if after else None
        delta = after_duration - before_duration if before_duration is not None and after_duration is not None else None
        percent_delta = round(delta / before_duration * 100, 1) if delta is not None and before_duration else None
        slower = bool(delta is not None and percent_delta is not None and delta > SLOWER_SECONDS_THRESHOLD and percent_delta > SLOWER_PERCENT_THRESHOLD)
        faster = bool(delta is not None and percent_delta is not None and delta < -SLOWER_SECONDS_THRESHOLD and percent_delta < -SLOWER_PERCENT_THRESHOLD)
        category = _category(before.get("status") if before else None, after.get("status") if after else None)
        counts[category] += 1
        slower_count += slower
        faster_count += faster
        rows.append({
            "test_case_id": case_id, "title": source.get("title") or f"Test case {case_id}",
            "priority": source.get("priority") or "medium", "execution_mode": source.get("execution_mode") or "manual",
            "category": category, "baseline_status": before.get("status") if before else None,
            "target_status": after.get("status") if after else None,
            "baseline_result_id": before.get("id") if before else None, "target_result_id": after.get("id") if after else None,
            "baseline_duration": before_duration, "target_duration": after_duration,
            "duration_delta": delta, "duration_absolute_delta": abs(delta) if delta is not None else None,
            "duration_percent_delta": percent_delta,
            "slower": slower, "faster": faster,
            "target_failure_message": after.get("failure_message") if after else None,
        })
    rows.sort(key=lambda row: (_CATEGORY_ORDER[row["category"]], _PRIORITY_ORDER.get(row["priority"], 99), row["title"].lower()))
    baseline_total = sum(_duration(item.get("duration")) or 0 for item in baseline_results)
    target_total = sum(_duration(item.get("duration")) or 0 for item in target_results)
    baseline_rate, target_rate = _pass_rate(baseline_results), _pass_rate(target_results)
    return {"rows": rows, "summary": {
        "counts": counts, "baseline_pass_rate": baseline_rate, "target_pass_rate": target_rate,
        "pass_rate_delta": round(target_rate - baseline_rate, 1) if baseline_rate is not None and target_rate is not None else None,
        "baseline_total_duration": baseline_total, "target_total_duration": target_total,
        "total_duration_delta": target_total - baseline_total, "slower_count": slower_count, "faster_count": faster_count,
    }}

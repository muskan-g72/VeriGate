"""Immutable test-case definitions captured when a verification run is created."""
from copy import deepcopy
from typing import Any

from app.models.test_case import TestCase


SNAPSHOT_FIELDS = (
    "title", "description", "steps", "expected_result", "priority",
    "is_active", "execution_mode", "automation_steps",
)


def build_test_case_snapshot(test_case: TestCase) -> dict[str, Any]:
    return {
        field: deepcopy(getattr(test_case, field))
        for field in SNAPSHOT_FIELDS
    }


def snapshot_value(result, field: str, default=None):
    """Prefer the immutable snapshot while retaining readable pre-versioning runs."""
    snapshot = getattr(result, "test_case_snapshot", None) or {}
    if field in snapshot:
        return snapshot[field]
    test_case = getattr(result, "test_case", None)
    return getattr(test_case, field, default) if test_case is not None else default

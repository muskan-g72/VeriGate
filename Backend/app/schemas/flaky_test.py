import uuid
from datetime import datetime

from pydantic import BaseModel


class FlakyTestHistoryPoint(BaseModel):
    status: str
    completed_at: datetime | None


class FlakyTestRead(BaseModel):
    test_case_id: uuid.UUID
    test_case_title: str
    test_suite_id: uuid.UUID
    test_suite_name: str
    executions: int
    passed: int
    failed: int
    flips: int
    stability_score: float
    latest_status: str
    history: list[FlakyTestHistoryPoint]

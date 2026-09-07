import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import EvidenceResponse

RunStatus = Literal["pending", "in_progress", "completed"]
ResultStatus = Literal["pending", "running", "passed", "failed", "blocked", "skipped"]
FINAL_RESULT_STATUSES = frozenset({"passed", "failed", "blocked", "skipped"})


class VerificationRunCreate(BaseModel):
    name: str = Field(default="Verification Run", min_length=1, max_length=160)


class VerificationResultUpdate(BaseModel):
    status: ResultStatus
    actual_result: str | None = None
    notes: str | None = None
    failure_message: str | None = None
    stack_trace: str | None = None
    duration: float | None = Field(default=None, ge=0)


class VerificationResultRead(BaseModel):
    id: uuid.UUID
    verification_run_id: uuid.UUID
    test_case_id: uuid.UUID
    status: ResultStatus
    actual_result: str | None
    notes: str | None
    failure_message: str | None
    stack_trace: str | None
    duration: float | None
    executed_at: datetime | None
    created_at: datetime
    evidence_items: list[EvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VerificationRunRead(BaseModel):
    id: uuid.UUID
    test_suite_id: uuid.UUID
    created_by_id: uuid.UUID
    name: str
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    total_cases: int
    pending_count: int
    passed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int

    model_config = ConfigDict(from_attributes=True)


class VerificationRunDetail(VerificationRunRead):
    results: list[VerificationResultRead]

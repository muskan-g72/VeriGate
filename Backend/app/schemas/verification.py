import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import EvidenceResponse
from app.schemas.quality_gate import QualityGateEvaluationRead

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
    trigger_source: str = "manual"
    pr_number: int | None = None
    pr_title: str | None = None
    pr_source_branch: str | None = None
    pr_target_branch: str | None = None
    pr_commit_sha: str | None = None
    pr_repository: str | None = None
    pr_author: str | None = None
    pr_url: str | None = None
    comment_status: str | None = None
    comment_url: str | None = None
    comment_error: str | None = None
    commit_status: str | None = None
    commit_status_url: str | None = None
    commit_status_error: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    total_cases: int
    pending_count: int
    passed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int
    quality_gate_evaluation: QualityGateEvaluationRead | None = None

    model_config = ConfigDict(from_attributes=True)


class VerificationRunDetail(VerificationRunRead):
    results: list[VerificationResultRead]


class ComparableRunRead(BaseModel):
    id: uuid.UUID
    label: str
    created_at: datetime
    status: RunStatus
    pass_rate: float | None = None
    gate_outcome: str | None = None


class RunComparisonRunRead(BaseModel):
    id: uuid.UUID
    name: str
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    pr_number: int | None = None
    pr_commit_sha: str | None = None
    gate_outcome: str | None = None


class RunComparisonRow(BaseModel):
    test_case_id: uuid.UUID
    title: str
    priority: str
    execution_mode: str
    category: str
    baseline_status: str | None = None
    target_status: str | None = None
    baseline_result_id: uuid.UUID | None = None
    target_result_id: uuid.UUID | None = None
    baseline_duration: float | None = None
    target_duration: float | None = None
    duration_delta: float | None = None
    duration_absolute_delta: float | None = None
    duration_percent_delta: float | None = None
    slower: bool = False
    faster: bool = False
    target_failure_message: str | None = None


class RunComparisonSummary(BaseModel):
    counts: dict[str, int]
    baseline_pass_rate: float | None = None
    target_pass_rate: float | None = None
    pass_rate_delta: float | None = None
    baseline_total_duration: float = 0
    target_total_duration: float = 0
    total_duration_delta: float = 0
    slower_count: int = 0
    faster_count: int = 0


class RunComparisonRead(BaseModel):
    baseline: RunComparisonRunRead
    target: RunComparisonRunRead
    summary: RunComparisonSummary
    rows: list[RunComparisonRow]
    gate_changed: bool = False

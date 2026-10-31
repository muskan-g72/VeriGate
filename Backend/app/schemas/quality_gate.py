import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Priority = Literal["low", "medium", "high", "critical"]

class QualityGateUpdate(BaseModel):
    enabled: bool = True
    min_pass_rate_enabled: bool = False
    min_pass_rate: float | None = Field(default=None, ge=0, le=100)
    critical_tests_enabled: bool = False
    critical_priorities: list[Priority] = Field(default_factory=lambda: ["critical"])
    critical_issues_enabled: bool = False
    min_executed_tests_enabled: bool = False
    min_executed_tests: int = Field(default=1, ge=1)
    treat_blocked_as_failure: bool = True

    @model_validator(mode="after")
    def require_enabled_thresholds(self):
        if self.min_pass_rate_enabled and self.min_pass_rate is None:
            raise ValueError("min_pass_rate is required when its rule is enabled")
        if self.critical_tests_enabled and not self.critical_priorities:
            raise ValueError("critical_priorities is required when its rule is enabled")
        return self

class QualityGateRead(QualityGateUpdate):
    id: uuid.UUID
    project_id: uuid.UUID
    updated_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QualityGateEvaluationRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    gate_id: uuid.UUID | None
    outcome: Literal["passed", "failed", "not_configured"]
    rules_snapshot: dict[str, Any]
    rule_results: list[dict[str, Any]]
    evaluated_at: datetime
    model_config = ConfigDict(from_attributes=True)

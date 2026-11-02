import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RequirementPriority = Literal["critical", "high", "medium", "low"]
RequirementCategory = Literal["functional", "non-functional", "security", "performance", "compliance", "other"]
RequirementStatus = Literal["draft", "approved", "deprecated"]


class RequirementCreate(BaseModel):
    requirement_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: RequirementPriority = "medium"
    category: RequirementCategory = "functional"
    status: RequirementStatus = "draft"
    source: str | None = None

    @field_validator("requirement_key", "title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class RequirementUpdate(BaseModel):
    requirement_key: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: RequirementPriority | None = None
    category: RequirementCategory | None = None
    status: RequirementStatus | None = None
    source: str | None = None

    @field_validator("requirement_key", "title")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class RequirementRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    requirement_key: str
    title: str
    description: str | None
    priority: RequirementPriority
    category: RequirementCategory
    status: RequirementStatus
    source: str | None
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequirementLinkedTestCaseRead(BaseModel):
    id: uuid.UUID
    title: str
    test_suite_id: uuid.UUID
    test_suite_name: str
    priority: str
    is_active: bool
    latest_result_id: uuid.UUID | None = None
    latest_run_id: uuid.UUID | None = None
    latest_run_completed_at: datetime | None = None
    latest_status: str | None = None


class RequirementLinkedIssueRead(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    severity: str
    priority: str


class RequirementTraceabilityRead(RequirementRead):
    coverage_status: Literal["untested", "passing", "failing", "not_passing"]
    linked_test_case_count: int
    passing_test_case_count: int
    not_passing_test_case_count: int
    unresolved_issue_count: int
    test_cases: list[RequirementLinkedTestCaseRead]
    issues: list[RequirementLinkedIssueRead]


class RequirementTraceabilityResponse(BaseModel):
    items: list[RequirementTraceabilityRead]
    total: int

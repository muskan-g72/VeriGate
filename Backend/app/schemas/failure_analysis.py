import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FailureCategory = Literal[
    "Assertion Failure",
    "Element Not Found",
    "Timeout",
    "Authentication Failure",
    "API Failure",
    "Database Failure",
    "Configuration Error",
    "Network Error",
    "Application Error",
    "Test Environment Error",
    "Unknown",
]


class FailureAnalysis(BaseModel):
    test_case_id: uuid.UUID
    test_case_title: str
    result_id: uuid.UUID
    status: str
    root_cause: str
    failure_category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    suggested_fix: str
    evidence_used: list[str] = Field(default_factory=list)
    analysis_source: Literal["llm", "heuristic_engine"] = "heuristic_engine"
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationRunAnalysisRequest(BaseModel):
    result_id: uuid.UUID | None = None


class VerificationRunAnalysisResponse(BaseModel):
    verification_run_id: uuid.UUID
    verification_run_name: str
    status: str
    has_failures: bool
    summary: str
    analyses: list[FailureAnalysis] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

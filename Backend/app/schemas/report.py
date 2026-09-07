from pydantic import BaseModel, Field


class VerificationReportSection(BaseModel):
    total_runs: int
    completed_runs: int
    in_progress_runs: int
    failed_runs: int


class TestsReportSection(BaseModel):
    total: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    pending: int
    pass_rate: float


class IssuesReportSection(BaseModel):
    open: int
    in_progress: int
    resolved: int
    closed: int


class ProjectReportResponse(BaseModel):
    verification: VerificationReportSection
    tests: TestsReportSection
    issues: IssuesReportSection


class VerificationTrendPoint(BaseModel):
    date: str
    runs: int
    passed: int
    failed: int
    blocked: int


class IssueReportResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    by_priority: dict[str, int]
    by_severity: dict[str, int]

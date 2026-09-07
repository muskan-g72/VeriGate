import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

SystemRole = Literal["admin", "user"]


class AdminStatisticsResponse(BaseModel):
    total_users: int
    total_projects: int
    total_teams: int
    total_test_cases: int
    total_verification_runs: int
    total_issues: int
    failed_results: int
    open_issues: int


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: SystemRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminProjectOwner(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None


class AdminProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner: AdminProjectOwner
    created_at: datetime
    updated_at: datetime
    member_count: int
    test_suite_count: int
    test_case_count: int
    verification_run_count: int
    open_issue_count: int


class AdminTeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    member_count: int
    created_at: datetime


class AdminVerificationRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    suite_id: uuid.UUID
    suite_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AdminIssueResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: str
    priority: str
    severity: str
    created_at: datetime
    updated_at: datetime

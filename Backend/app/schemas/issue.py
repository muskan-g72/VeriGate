import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

IssueSeverity = Literal["low", "medium", "high", "critical"]
IssueStatus = Literal["open", "in_progress", "resolved", "closed"]


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = None
    severity: IssueSeverity = "medium"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str) -> str:
        stripped_title = title.strip()
        if not stripped_title:
            raise ValueError("Issue title cannot be blank")
        return stripped_title


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    severity: IssueSeverity | None = None
    status: IssueStatus | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, title: str | None) -> str | None:
        if title is None:
            return None
        stripped_title = title.strip()
        if not stripped_title:
            raise ValueError("Issue title cannot be blank")
        return stripped_title


class IssueRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    verification_result_id: uuid.UUID
    reported_by_id: uuid.UUID
    title: str
    description: str | None
    severity: IssueSeverity
    status: IssueStatus
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

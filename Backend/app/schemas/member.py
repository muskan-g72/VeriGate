import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectMemberRole = Literal[
    "owner",
    "manager",
    "qa_lead",
    "tester",
    "developer",
    "viewer",
]


class ProjectMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: ProjectMemberRole = "viewer"


class ProjectMemberUpdate(BaseModel):
    role: ProjectMemberRole


class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: ProjectMemberRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TeamMemberRole = Literal["lead", "member"]


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        stripped = name.strip()
        if not stripped:
            raise ValueError("Team name cannot be blank")
        return stripped


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        stripped = name.strip()
        if not stripped:
            raise ValueError("Team name cannot be blank")
        return stripped


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: TeamMemberRole = "member"


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: TeamMemberRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)

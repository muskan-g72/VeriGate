import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EvidenceType = Literal["screenshot", "log", "error", "text", "trace"]


class EvidenceCreate(BaseModel):
    type: EvidenceType
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    content: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Evidence name cannot be blank")
        return stripped_name


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    verification_result_id: uuid.UUID
    type: EvidenceType
    name: str
    description: str | None
    content: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

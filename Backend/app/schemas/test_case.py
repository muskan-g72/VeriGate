import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Priority = Literal["low", "medium", "high", "critical"]


class TestCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    steps: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    priority: Priority = "medium"

    @field_validator("title", "steps", "expected_result")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Value cannot be blank")
        return stripped_value


class TestCaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    steps: str | None = Field(default=None, min_length=1)
    expected_result: str | None = Field(default=None, min_length=1)
    priority: Priority | None = None
    is_active: bool | None = None

    @field_validator("title", "steps", "expected_result")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Value cannot be blank")
        return stripped_value


class TestCaseRead(BaseModel):
    id: uuid.UUID
    test_suite_id: uuid.UUID
    title: str
    description: str | None
    steps: str
    expected_result: str
    priority: Priority
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

Priority = Literal["low", "medium", "high", "critical"]
ExecutionMode = Literal["manual", "automated"]
PLAYWRIGHT_ACTIONS = frozenset(
    {"goto", "click", "fill", "expect_text", "expect_title"}
)


class AutomationStep(BaseModel):
    action: str
    selector: str | None = None
    value: str | None = None

    model_config = ConfigDict(extra="allow")

    @model_serializer(mode="wrap")
    def omit_null_fields(self, serializer):
        data = serializer(self)
        return {key: value for key, value in data.items() if value is not None}

    @field_validator("action")
    @classmethod
    def require_supported_action(cls, action: str) -> str:
        normalized_action = action.strip()
        if normalized_action not in PLAYWRIGHT_ACTIONS:
            raise ValueError(f"Unsupported Playwright action: {action}")
        return normalized_action

    @model_validator(mode="after")
    def require_action_fields(self) -> "AutomationStep":
        if self.action == "goto" and not self.value:
            raise ValueError("'goto' requires 'value'")
        if self.action == "click" and not self.selector:
            raise ValueError("'click' requires 'selector'")
        if self.action == "fill":
            if not self.selector:
                raise ValueError("'fill' requires 'selector'")
            if self.value is None:
                raise ValueError("'fill' requires 'value'")
        if self.action == "expect_text" and self.value is None:
            raise ValueError("'expect_text' requires 'value'")
        if self.action == "expect_title" and self.value is None:
            raise ValueError("'expect_title' requires 'value'")
        return self


def validate_automation_steps(
    automation_steps: list[Any] | None,
) -> list[dict[str, Any]] | None:
    if automation_steps is None:
        return None
    if not isinstance(automation_steps, list):
        raise ValueError("automation_steps must be a list of step objects")
    return [
        AutomationStep.model_validate(step).model_dump(exclude_none=True)
        for step in automation_steps
    ]


def validate_test_case_automation(
    execution_mode: str,
    automation_steps: list[Any] | None,
) -> list[dict[str, Any]] | None:
    normalized_steps = validate_automation_steps(automation_steps)
    if execution_mode == "automated":
        if not normalized_steps:
            raise ValueError("Automated test cases require automation_steps")
    return normalized_steps


class TestCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    steps: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    priority: Priority = "medium"
    execution_mode: ExecutionMode = "manual"
    automation_steps: list[AutomationStep] | None = None

    @field_validator("title", "steps", "expected_result")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Value cannot be blank")
        return stripped_value

    @model_validator(mode="after")
    def require_steps_for_automated_cases(self) -> "TestCaseCreate":
        validate_test_case_automation(self.execution_mode, self.automation_steps)
        return self


class TestCaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    steps: str | None = Field(default=None, min_length=1)
    expected_result: str | None = Field(default=None, min_length=1)
    priority: Priority | None = None
    is_active: bool | None = None
    execution_mode: ExecutionMode | None = None
    automation_steps: list[AutomationStep] | None = None

    @field_validator("title", "steps", "expected_result")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Value cannot be blank")
        return stripped_value

    @model_validator(mode="after")
    def validate_automation_payload(self) -> "TestCaseUpdate":
        fields_set = self.model_fields_set
        if "automation_steps" in fields_set:
            validate_automation_steps(self.automation_steps)
        if self.execution_mode == "automated" and "automation_steps" in fields_set:
            validate_test_case_automation(self.execution_mode, self.automation_steps)
        return self


class TestCaseRead(BaseModel):
    id: uuid.UUID
    test_suite_id: uuid.UUID
    title: str
    description: str | None
    steps: str
    expected_result: str
    priority: Priority
    is_active: bool
    execution_mode: ExecutionMode
    automation_steps: list[AutomationStep] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

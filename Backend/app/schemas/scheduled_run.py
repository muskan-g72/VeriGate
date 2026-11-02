import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScheduledRunCreate(BaseModel):
    name: str = Field(default="Scheduled verification", min_length=1, max_length=160)
    interval_minutes: int = Field(ge=5, le=43_200, description="Minutes between runs; 1440 is daily.")
    enabled: bool = True


class ScheduledRunUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    interval_minutes: int | None = Field(default=None, ge=5, le=43_200)
    enabled: bool | None = None


class ScheduledRunRead(BaseModel):
    id: uuid.UUID
    test_suite_id: uuid.UUID
    created_by_id: uuid.UUID
    name: str
    interval_minutes: int
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None = None
    last_run_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

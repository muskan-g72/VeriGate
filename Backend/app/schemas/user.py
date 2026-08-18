import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).lower()


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

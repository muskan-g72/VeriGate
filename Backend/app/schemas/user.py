from typing import Literal

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str = Field(default="user")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, role: str) -> str:
        if not role:
            return "user"
        normalized = role.strip().lower()
        if normalized not in ("user", "admin"):
            raise ValueError("Role must be either 'USER' or 'ADMIN'")
        return normalized


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str = "user"
    system_role: str = "user"
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "user"]


class UserStatusUpdate(BaseModel):
    is_active: bool

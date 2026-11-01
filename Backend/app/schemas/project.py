import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    github_repo: str | None = None
    github_default_branch: str | None = "main"
    github_verification_enabled: bool = True
    github_webhook_secret: str | None = None
    github_token: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Project name cannot be blank")
        return stripped_name


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    github_repo: str | None = None
    github_default_branch: str | None = None
    github_verification_enabled: bool | None = None
    github_webhook_secret: str | None = None
    github_token: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Project name cannot be blank")
        return stripped_name


class ProjectGitHubConfigUpdate(BaseModel):
    github_repo: str | None = None
    github_default_branch: str | None = None
    github_verification_enabled: bool | None = None
    github_webhook_secret: str | None = None
    github_token: str | None = None
    pr_comments_enabled: bool | None = None
    comment_include_ai: bool | None = None
    comment_max_failures: int | None = Field(default=None, ge=1, le=25)


class ProjectGitHubConfigResponse(BaseModel):
    project_id: uuid.UUID
    github_repo: str | None = None
    github_default_branch: str | None = "main"
    github_verification_enabled: bool = True
    is_connected: bool = False
    webhook_configured: bool = False
    token_configured: bool = False
    webhook_url: str = ""
    pr_comments_enabled: bool = False
    comment_include_ai: bool = True
    comment_max_failures: int = 10


class ProjectRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    github_repo: str | None = None
    github_default_branch: str | None = None
    github_verification_enabled: bool = True
    github_webhook_configured: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

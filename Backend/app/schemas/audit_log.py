import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AuditLogUserSummary(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    project_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    description: str | None
    created_at: datetime
    user: AuditLogUserSummary | None = None

    model_config = ConfigDict(from_attributes=True)

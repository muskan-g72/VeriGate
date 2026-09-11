import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.issue import Issue
    from app.models.project_member import ProjectMember
    from app.models.test_suite import TestSuite
    from app.models.user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    github_repo: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    github_default_branch: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="main",
    )
    github_verification_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    github_webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    test_suites: Mapped[list["TestSuite"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="project",
    )

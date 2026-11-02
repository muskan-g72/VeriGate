import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Table, Text, UniqueConstraint, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.project import Project
    from app.models.test_case import TestCase
    from app.models.user import User


requirement_test_cases = Table(
    "requirement_test_cases",
    Base.metadata,
    Column("requirement_id", ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True),
    Column("test_case_id", ForeignKey("test_cases.id", ondelete="CASCADE"), primary_key=True),
)

issue_requirements = Table(
    "issue_requirements",
    Base.metadata,
    Column("issue_id", ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
    Column("requirement_id", ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True),
)


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("project_id", "requirement_key", name="uq_requirement_project_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", server_default="medium", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), default="functional", server_default="functional", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="requirements")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="requirements", secondary=requirement_test_cases)
    issues: Mapped[list["Issue"]] = relationship(back_populates="requirements", secondary=issue_requirements)

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.test_case import TestCase
    from app.models.user import User
    from app.models.verification_result import VerificationResult
    from app.models.verification_run import VerificationRun


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_results.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verification_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("verification_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reported_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        server_default="medium",
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        server_default="medium",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="open",
        server_default="open",
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    project: Mapped["Project"] = relationship(back_populates="issues")
    verification_result: Mapped["VerificationResult"] = relationship(
        back_populates="issues"
    )
    test_case: Mapped["TestCase | None"] = relationship()
    verification_run: Mapped["VerificationRun | None"] = relationship()
    reported_by: Mapped["User"] = relationship(
        back_populates="reported_issues",
        foreign_keys=[reported_by_id],
    )
    assigned_to: Mapped["User | None"] = relationship(
        back_populates="assigned_issues",
        foreign_keys=[assigned_to_id],
    )

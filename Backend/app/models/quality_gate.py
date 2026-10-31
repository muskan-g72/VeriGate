import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.verification_run import VerificationRun


class QualityGate(Base):
    __tablename__ = "quality_gates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_pass_rate_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_pass_rate: Mapped[float | None] = mapped_column(nullable=True)
    critical_tests_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    critical_priorities: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["critical"], nullable=False)
    critical_issues_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_executed_tests_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_executed_tests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    treat_blocked_as_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="quality_gate")
    updated_by: Mapped["User | None"] = relationship(foreign_keys=[updated_by_id])
    evaluations: Mapped[list["QualityGateEvaluation"]] = relationship(back_populates="gate")


class QualityGateEvaluation(Base):
    __tablename__ = "quality_gate_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verification_runs.id", ondelete="CASCADE"), unique=True, index=True)
    gate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("quality_gates.id", ondelete="SET NULL"), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="not_configured")
    rules_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rule_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped["VerificationRun"] = relationship(back_populates="quality_gate_evaluation")
    gate: Mapped["QualityGate | None"] = relationship(back_populates="evaluations")

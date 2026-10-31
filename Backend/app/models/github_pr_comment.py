import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GitHubPrComment(Base):
    """The single updatable VeriGate summary comment for a project PR."""

    __tablename__ = "github_pr_comments"
    __table_args__ = (UniqueConstraint("project_id", "repository", "pr_number", name="uq_github_pr_comment_project_repo_pr"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    github_comment_id: Mapped[int | None] = mapped_column(nullable=True)
    comment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("verification_runs.id", ondelete="SET NULL"), nullable=True)
    last_status: Mapped[str] = mapped_column(String(20), nullable=False, default="skipped")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

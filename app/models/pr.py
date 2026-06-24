"""PullRequest ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PRStatus(str, enum.Enum):
    WAITING_REVIEW = "WAITING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    READY_TO_MERGE = "READY_TO_MERGE"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_pr_number: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[PRStatus] = mapped_column(
        Enum(PRStatus), default=PRStatus.WAITING_REVIEW, nullable=False
    )
    priority: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    labels: Mapped[str] = mapped_column(String(1024), default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    github_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    assignments: Mapped[list["ReviewerAssignment"]] = relationship(
        "ReviewerAssignment",
        back_populates="pr",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PullRequest #{self.github_pr_number} [{self.status}]>"

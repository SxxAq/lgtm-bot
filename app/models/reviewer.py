"""ReviewerAssignment ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssignmentState(str, enum.Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


class ReviewerAssignment(Base):
    __tablename__ = "reviewer_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pull_requests.id"), nullable=False
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_username: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[AssignmentState] = mapped_column(
        Enum(AssignmentState), default=AssignmentState.STARTED, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    pr: Mapped["PullRequest"] = relationship("PullRequest", back_populates="assignments")

    def __repr__(self) -> str:
        return (
            f"<ReviewerAssignment pr_id={self.pr_id} "
            f"user=@{self.telegram_username} state={self.state}>"
        )

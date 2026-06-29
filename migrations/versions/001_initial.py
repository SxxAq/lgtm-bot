"""Initial schema — creates pull_requests, reviewer_assignments, users tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("github_pr_number", sa.Integer, nullable=False),
        sa.Column("repo", sa.String(256), nullable=False, server_default="fossasia/eventyay"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("author", sa.String(128), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "WAITING_REVIEW", "IN_REVIEW", "READY_TO_MERGE",
                "CHANGES_REQUESTED", "MERGED", "CLOSED",
                name="prstatus",
            ),
            nullable=False,
            server_default="WAITING_REVIEW",
        ),
        sa.Column("priority", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("labels", sa.String(1024), server_default="[]"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("github_created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_pull_requests_github_pr_number", "pull_requests", ["github_pr_number"])

    op.create_table(
        "reviewer_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pr_id", sa.Integer, sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
        sa.Column("telegram_username", sa.String(128), nullable=False),
        sa.Column(
            "state",
            sa.Enum("STARTED", "COMPLETED", name="assignmentstate"),
            nullable=False,
            server_default="STARTED",
        ),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger, unique=True, nullable=False),
        sa.Column("telegram_username", sa.String(128), nullable=False),
        sa.Column("reviews_started", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reviews_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_review_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"])


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("reviewer_assignments")
    op.drop_index("ix_pull_requests_github_pr_number", "pull_requests")
    op.drop_table("pull_requests")

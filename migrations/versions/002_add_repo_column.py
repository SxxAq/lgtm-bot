"""Add repo column to pull_requests table.

Revision ID: 002
Revises: 001
Create Date: 2026-06-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("pull_requests")]
    if "repo" not in columns:
        op.add_column(
            "pull_requests",
            sa.Column(
                "repo",
                sa.String(256),
                nullable=False,
                server_default="your-org/your-repo",
            ),
        )


def downgrade() -> None:
    op.drop_column("pull_requests", "repo")

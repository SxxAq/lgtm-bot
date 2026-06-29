"""Async SQLAlchemy engine, session factory, and Base."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


_connect_args = (
    {"check_same_thread": False}
    if "sqlite" in settings.DATABASE_URL
    else {}
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables and self-heal missing columns."""
    from app.models import pr, reviewer, user  # noqa: F401
    from sqlalchemy import inspect, text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _heal_columns(sync_conn):
            inspector = inspect(sync_conn)
            if "pull_requests" in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns("pull_requests")]
                if "repo" not in cols:
                    sync_conn.execute(
                        text("ALTER TABLE pull_requests ADD COLUMN repo VARCHAR(256) DEFAULT 'your-org/your-repo'")
                    )

                # SQLite table migration if github_pr_number has unique constraint in sqlite_master
                if "sqlite" in db_url:
                    res = sync_conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='pull_requests'")).scalar()
                    if res and ("github_pr_number INTEGER UNIQUE" in res or "github_pr_number INTEGER NOT NULL UNIQUE" in res or "UNIQUE (github_pr_number)" in res):
                        sync_conn.execute(text("CREATE TABLE pull_requests_dg_tmp (id INTEGER PRIMARY KEY, github_pr_number INTEGER NOT NULL, repo VARCHAR(256) NOT NULL DEFAULT 'your-org/your-repo', title VARCHAR(512) NOT NULL, author VARCHAR(128) NOT NULL, url VARCHAR(512) NOT NULL, status VARCHAR(17) NOT NULL DEFAULT 'WAITING_REVIEW', priority BOOLEAN NOT NULL DEFAULT 0, labels VARCHAR(1024) DEFAULT '[]', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, github_created_at DATETIME)"))
                        sync_conn.execute(text("INSERT INTO pull_requests_dg_tmp SELECT id, github_pr_number, repo, title, author, url, status, priority, labels, created_at, updated_at, github_created_at FROM pull_requests"))
                        sync_conn.execute(text("DROP TABLE pull_requests"))
                        sync_conn.execute(text("ALTER TABLE pull_requests_dg_tmp RENAME TO pull_requests"))
                        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pull_requests_github_pr_number ON pull_requests (github_pr_number)"))

        await conn.run_sync(_heal_columns)

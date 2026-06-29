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
                        text("ALTER TABLE pull_requests ADD COLUMN repo VARCHAR(256) DEFAULT 'fossasia/eventyay'")
                    )

        await conn.run_sync(_heal_columns)

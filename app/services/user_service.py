"""User service — create/update users and track stats."""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


async def get_or_create_user(
    session: AsyncSession,
    telegram_user_id: int,
    telegram_username: str,
) -> User:
    """Get existing user or create a new one. Always syncs username."""
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
        )
        session.add(user)
        await session.flush()
        logger.info("Created new user record: @%s (id=%d)", telegram_username, telegram_user_id)
    else:
        # Keep username up-to-date (Telegram usernames can change)
        user.telegram_username = telegram_username

    return user


async def increment_started(session: AsyncSession, telegram_user_id: int) -> None:
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.reviews_started += 1


async def increment_completed(session: AsyncSession, telegram_user_id: int) -> None:
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.reviews_completed += 1

    # Streak logic
    today = date.today()
    if user.last_review_date is None:
        user.current_streak = 1
    elif (today - user.last_review_date).days == 1:
        user.current_streak += 1  # consecutive day
    elif (today - user.last_review_date).days == 0:
        pass  # same day, no change
    else:
        user.current_streak = 1  # streak broken

    user.last_review_date = today
    user.longest_streak = max(user.longest_streak, user.current_streak)


async def get_all_users(session: AsyncSession) -> list[User]:
    """All users ordered by reviews completed (descending)."""
    result = await session.execute(
        select(User).order_by(User.reviews_completed.desc())
    )
    return list(result.scalars().all())

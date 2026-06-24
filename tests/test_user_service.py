"""Unit tests for user_service."""
from __future__ import annotations

import pytest

from app.services import user_service


class TestGetOrCreateUser:
    @pytest.mark.asyncio
    async def test_creates_new_user(self, db_session):
        user = await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()
        assert user.telegram_user_id == 1001
        assert user.telegram_username == "aqueel"
        assert user.reviews_started == 0
        assert user.reviews_completed == 0
        assert user.current_streak == 0

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, db_session):
        u1 = await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()
        u2 = await user_service.get_or_create_user(db_session, 1001, "aqueel_updated")
        assert u1.id == u2.id
        assert u2.telegram_username == "aqueel_updated"  # Username sync

    @pytest.mark.asyncio
    async def test_different_users_created_separately(self, db_session):
        u1 = await user_service.get_or_create_user(db_session, 1001, "aqueel")
        u2 = await user_service.get_or_create_user(db_session, 1002, "aqil")
        await db_session.commit()
        assert u1.id != u2.id


class TestCounters:
    @pytest.mark.asyncio
    async def test_increment_started(self, db_session):
        await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()
        await user_service.increment_started(db_session, 1001)
        await db_session.commit()
        await user_service.increment_started(db_session, 1001)
        await db_session.commit()
        users = await user_service.get_all_users(db_session)
        assert users[0].reviews_started == 2

    @pytest.mark.asyncio
    async def test_increment_completed(self, db_session):
        await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()
        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()
        users = await user_service.get_all_users(db_session)
        assert users[0].reviews_completed == 1
        assert users[0].current_streak == 1
        assert users[0].longest_streak == 1

    @pytest.mark.asyncio
    async def test_streak_increments_on_next_day(self, db_session):
        from datetime import date, timedelta
        await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()

        # First completion
        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()

        # Manually set last_review_date to yesterday
        from sqlalchemy import select
        from app.models.user import User
        result = await db_session.execute(select(User).where(User.telegram_user_id == 1001))
        user = result.scalar_one()
        user.last_review_date = date.today() - timedelta(days=1)
        await db_session.commit()

        # Second completion (should extend streak)
        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()
        result = await db_session.execute(select(User).where(User.telegram_user_id == 1001))
        user = result.scalar_one()
        assert user.current_streak == 2
        assert user.longest_streak == 2

    @pytest.mark.asyncio
    async def test_streak_resets_after_gap(self, db_session):
        from datetime import date, timedelta
        from sqlalchemy import select
        from app.models.user import User

        await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await db_session.commit()
        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()

        # Set last review date to 3 days ago (streak broken)
        result = await db_session.execute(select(User).where(User.telegram_user_id == 1001))
        user = result.scalar_one()
        user.current_streak = 5  # Manually set high streak
        user.last_review_date = date.today() - timedelta(days=3)
        await db_session.commit()

        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()
        result = await db_session.execute(select(User).where(User.telegram_user_id == 1001))
        user = result.scalar_one()
        assert user.current_streak == 1  # Reset


class TestGetAllUsers:
    @pytest.mark.asyncio
    async def test_sorted_by_completed_desc(self, db_session):
        await user_service.get_or_create_user(db_session, 1001, "aqueel")
        await user_service.get_or_create_user(db_session, 1002, "aqil")
        await db_session.commit()

        await user_service.increment_completed(db_session, 1001)
        await user_service.increment_completed(db_session, 1001)
        await db_session.commit()
        await user_service.increment_completed(db_session, 1002)
        await db_session.commit()

        users = await user_service.get_all_users(db_session)
        assert users[0].telegram_username == "aqueel"
        assert users[1].telegram_username == "aqil"

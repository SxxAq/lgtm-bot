"""APScheduler job definitions and scheduler factory."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode

from app.config import settings
from app.database import AsyncSessionLocal
from app.services import pr_service
from app.telegram import formatters as fmt

logger = logging.getLogger(__name__)


async def sync_job(bot: Bot) -> None:
    """Sync all tracked open PRs with GitHub. Runs every 30 minutes."""
    logger.info("Running scheduled PR sync…")
    try:
        async with AsyncSessionLocal() as session:
            result = await pr_service.sync_prs(session)
        logger.info("Sync complete: %s", result)
    except Exception:
        logger.exception("Error during scheduled sync")


async def daily_digest_job(bot: Bot) -> None:
    """Post the daily review summary to the group. Runs once per day."""
    if not settings.GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not set — skipping daily digest")
        return

    logger.info("Sending daily digest to chat %d…", settings.GROUP_CHAT_ID)
    try:
        async with AsyncSessionLocal() as session:
            board = await pr_service.get_board(session)
            stats = await pr_service.get_stats(session)

        message = fmt.fmt_daily_digest(board, stats)
        await bot.send_message(
            chat_id=settings.GROUP_CHAT_ID,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.info("Daily digest sent successfully")
    except Exception:
        logger.exception("Error sending daily digest")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Build and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        sync_job,
        trigger="interval",
        minutes=30,
        args=[bot],
        id="pr_sync",
        name="GitHub PR Sync",
        replace_existing=True,
    )

    scheduler.add_job(
        daily_digest_job,
        trigger="cron",
        hour=settings.DIGEST_HOUR,
        minute=settings.DIGEST_MINUTE,
        args=[bot],
        id="daily_digest",
        name="Daily Review Digest",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured — sync: every 30min, digest: %02d:%02d UTC",
        settings.DIGEST_HOUR,
        settings.DIGEST_MINUTE,
    )
    return scheduler

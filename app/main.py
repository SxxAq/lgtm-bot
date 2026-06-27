"""LGTM Bot entry point."""
from __future__ import annotations

import asyncio
import logging
import sys

from app.config import settings
from app.telegram.bot import create_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Reduce noise from httpx and telegram libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    logger.info("━" * 50)
    logger.info("Starting LGTM Bot")
    logger.info("Repo    : %s", settings.GITHUB_REPO)
    logger.info("Chat ID : %s", settings.GROUP_CHAT_ID or "not set")
    logger.info("Mode    : %s", "WEBHOOK" if settings.webhook_mode else "POLLING")
    logger.info("━" * 50)

    application = create_application()

    if settings.webhook_mode:
        logger.info("Webhook URL: %s%s", settings.WEBHOOK_URL, settings.WEBHOOK_PATH)
        application.run_webhook(
            listen="0.0.0.0",
            port=settings.WEBHOOK_PORT,
            url_path=settings.WEBHOOK_PATH,
            webhook_url=f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}",
            allowed_updates=["message", "callback_query"],
        )
    else:
        logger.info("Polling mode active — no WEBHOOK_URL configured")
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()

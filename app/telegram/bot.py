"""PTB Application factory — wires up handlers, DB, and scheduler."""
from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from app.commands.inline_buttons import button_callback_handler
from app.commands.pr_commands import handle_pr_command
from app.config import settings
from app.database import init_db
from app.scheduler.jobs import setup_scheduler

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Called once after the bot application is ready."""
    await init_db()
    logger.info("Database ready")

    scheduler = setup_scheduler(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Scheduler started")

    await application.bot.set_my_commands([
        BotCommand("pr", "PR review queue — use /pr help for commands"),
    ])
    logger.info("Bot commands registered")


async def post_shutdown(application: Application) -> None:
    """Clean up on shutdown."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.telegram.formatters import fmt_help
    await update.message.reply_text(
        "👋 Welcome to <b>LGTM Bot</b>!\n\n"
        "I help the Eventyay team manage PR reviews in one place.\n\n"
        + fmt_help(),
        parse_mode=ParseMode.HTML,
    )


async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.telegram.formatters import fmt_help
    await update.message.reply_text(fmt_help(), parse_mode=ParseMode.HTML)


def create_application() -> Application:
    """Build the PTB Application with all handlers registered."""
    app = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("help", _help))
    app.add_handler(CommandHandler("pr", handle_pr_command))
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    logger.info("Bot application created with all handlers registered")
    return app

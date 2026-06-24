"""Inline keyboard button callback handler."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.database import AsyncSessionLocal
from app.services import pr_service
from app.telegram import formatters as fmt
from app.telegram.keyboards import board_refresh_keyboard, pr_action_keyboard
from app.utils.exceptions import DuplicateAssignment, LGTMBotError, NotAReviewer, PRNotFound

logger = logging.getLogger(__name__)


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "unknown"
    data = query.data or ""

    try:
        if data.startswith("take:"):
            pr_number = int(data.split(":")[1])
            async with AsyncSessionLocal() as session:
                pr = await pr_service.take_pr(session, pr_number, user_id, username)
            await query.edit_message_text(
                fmt.fmt_pr_taken(pr),
                parse_mode=ParseMode.HTML,
                reply_markup=pr_action_keyboard(pr_number),
                disable_web_page_preview=True,
            )

        elif data.startswith("done:"):
            pr_number = int(data.split(":")[1])
            async with AsyncSessionLocal() as session:
                pr = await pr_service.done_pr(session, pr_number, user_id, username)
            await query.edit_message_text(
                fmt.fmt_pr_done(pr, username),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        elif data.startswith("priority:"):
            pr_number = int(data.split(":")[1])
            async with AsyncSessionLocal() as session:
                pr = await pr_service.priority_pr(session, pr_number)
            await query.edit_message_text(
                fmt.fmt_pr_priority(pr, username),
                parse_mode=ParseMode.HTML,
                reply_markup=pr_action_keyboard(pr_number),
                disable_web_page_preview=True,
            )

        elif data == "board":
            async with AsyncSessionLocal() as session:
                board = await pr_service.get_board(session)
            await query.edit_message_text(
                fmt.fmt_board(board),
                parse_mode=ParseMode.HTML,
                reply_markup=board_refresh_keyboard(),
                disable_web_page_preview=True,
            )

        else:
            logger.warning("Unknown callback data: %s", data)

    except DuplicateAssignment as e:
        await query.answer(str(e), show_alert=True)
    except NotAReviewer as e:
        await query.answer(str(e), show_alert=True)
    except PRNotFound as e:
        await query.answer(str(e), show_alert=True)
    except LGTMBotError as e:
        await query.answer(str(e), show_alert=True)
    except Exception:
        logger.exception("Unexpected error in button callback: %s", data)
        await query.answer("An error occurred. Please try again.", show_alert=True)

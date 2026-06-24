"""PTB command handlers for /pr and all its subcommands."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.pr import PRStatus
from app.models.reviewer import AssignmentState
from app.services import pr_service
from app.telegram import formatters as fmt
from app.telegram.keyboards import board_refresh_keyboard, pr_action_keyboard
from app.utils.exceptions import (
    DuplicateAssignment,
    GitHubAPIError,
    LGTMBotError,
    NoPRsAvailable,
    NotAReviewer,
    PRAlreadyExists,
    PRNotFound,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_info(update: Update) -> tuple[int, str]:
    """Return (user_id, username) from the update."""
    user = update.effective_user
    return user.id, user.username or user.first_name or "unknown"


async def _reply(update: Update, text: str, **kwargs) -> None:
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        **kwargs,
    )


def _is_admin(username: str) -> bool:
    admin_list = settings.admin_list
    if not admin_list:
        return True  # No restriction if list is empty
    return username.lower() in admin_list


def _require_pr_number(args: list[str], usage: str) -> int | None:
    """Return int PR number or None (invalid)."""
    if len(args) < 2 or not args[1].isdigit():
        return None
    return int(args[1])


# ── Main dispatcher ───────────────────────────────────────────────────────────

async def handle_pr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route /pr <subcommand> to the appropriate handler."""
    if not context.args:
        await _reply(update, fmt.fmt_help())
        return

    subcommand = context.args[0].lower()

    HANDLERS = {
        "add":         _pr_add,
        "take":        _pr_take,
        "done":        _pr_done,
        "priority":    _pr_priority,
        "board":       _pr_board,
        "pick":        _pr_pick,
        "pending":     _pr_pending,
        "mine":        _pr_mine,
        "stats":       _pr_stats,
        "leaderboard": _pr_leaderboard,
        "streak":      _pr_streak,
        "aging":       _pr_aging,
        "sync":        _pr_sync,
        "force-close": _pr_force_close,
        "remove":      _pr_remove,
        "status":      _pr_status,
        "help":        _pr_help,
    }

    handler = HANDLERS.get(subcommand)
    if handler is None:
        await _reply(
            update,
            f"❓ Unknown subcommand: <code>{subcommand}</code>\n\n"
            "Use /pr help for a list of commands.",
        )
        return

    try:
        await handler(update, context)
    except (PRNotFound, PRAlreadyExists, DuplicateAssignment, NotAReviewer, NoPRsAvailable) as e:
        await _reply(update, fmt.fmt_error(str(e)))
    except GitHubAPIError as e:
        await _reply(update, fmt.fmt_error(f"GitHub API error: {e}"))
    except LGTMBotError as e:
        await _reply(update, fmt.fmt_error(str(e)))
    except Exception:
        logger.exception("Unexpected error in /pr %s", subcommand)
        await _reply(update, fmt.fmt_error("An unexpected error occurred. Please try again."))


# ── Subcommand handlers ───────────────────────────────────────────────────────

async def _pr_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pr_number = _require_pr_number(context.args, "/pr add <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr add &lt;number&gt;\nExample: /pr add 3975")
        return

    async with AsyncSessionLocal() as session:
        pr = await pr_service.add_pr(session, pr_number)

    await _reply(
        update,
        fmt.fmt_pr_added(pr),
        reply_markup=pr_action_keyboard(pr.github_pr_number),
    )


async def _pr_take(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pr_number = _require_pr_number(context.args, "/pr take <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr take &lt;number&gt;\nExample: /pr take 3975")
        return

    user_id, username = _user_info(update)
    async with AsyncSessionLocal() as session:
        pr = await pr_service.take_pr(session, pr_number, user_id, username)

    await _reply(update, fmt.fmt_pr_taken(pr))


async def _pr_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pr_number = _require_pr_number(context.args, "/pr done <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr done &lt;number&gt;\nExample: /pr done 3975")
        return

    user_id, username = _user_info(update)
    async with AsyncSessionLocal() as session:
        pr = await pr_service.done_pr(session, pr_number, user_id, username)

    await _reply(update, fmt.fmt_pr_done(pr, username))


async def _pr_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pr_number = _require_pr_number(context.args, "/pr priority <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr priority &lt;number&gt;\nExample: /pr priority 3975")
        return

    _, username = _user_info(update)
    async with AsyncSessionLocal() as session:
        pr = await pr_service.priority_pr(session, pr_number)

    await _reply(update, fmt.fmt_pr_priority(pr, username))


async def _pr_board(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        board = await pr_service.get_board(session)

    await _reply(update, fmt.fmt_board(board), reply_markup=board_refresh_keyboard())


async def _pr_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id, username = _user_info(update)
    async with AsyncSessionLocal() as session:
        pr = await pr_service.pick_pr(session, user_id, username)
        # Count active reviewers excluding the current user (for display)
        prior_active = sum(
            1
            for a in pr.assignments
            if a.state == AssignmentState.STARTED and a.telegram_user_id != user_id
        )

    await _reply(
        update,
        fmt.fmt_pr_picked(pr, prior_active),
        reply_markup=pr_action_keyboard(pr.github_pr_number),
    )


async def _pr_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        prs = await pr_service.get_pending(session)
    await _reply(update, fmt.fmt_pending(prs))


async def _pr_mine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id, username = _user_info(update)
    async with AsyncSessionLocal() as session:
        prs = await pr_service.get_my_reviews(session, user_id)
    await _reply(update, fmt.fmt_my_reviews(prs, username))


async def _pr_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        stats = await pr_service.get_stats(session)
    await _reply(update, fmt.fmt_stats(stats))


async def _pr_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        stats = await pr_service.get_stats(session)
    await _reply(update, fmt.fmt_leaderboard(stats))


async def _pr_streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        stats = await pr_service.get_stats(session)
    await _reply(update, fmt.fmt_streaks(stats))


async def _pr_aging(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        aging = await pr_service.get_aging(session)
    await _reply(update, fmt.fmt_aging(aging))


async def _pr_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, username = _user_info(update)
    if not _is_admin(username):
        await _reply(update, "🔒 This command is restricted to admins.")
        return

    await _reply(update, "🔄 Syncing with GitHub…")
    async with AsyncSessionLocal() as session:
        result = await pr_service.sync_prs(session)
    await _reply(update, fmt.fmt_sync_result(result))


async def _pr_force_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, username = _user_info(update)
    if not _is_admin(username):
        await _reply(update, "🔒 This command is restricted to admins.")
        return

    pr_number = _require_pr_number(context.args, "/pr force-close <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr force-close &lt;number&gt;")
        return

    async with AsyncSessionLocal() as session:
        pr = await pr_service.force_close_pr(session, pr_number)
    await _reply(update, f"🔒 PR <code>#{pr.github_pr_number}</code> has been force-closed.")


async def _pr_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, username = _user_info(update)
    if not _is_admin(username):
        await _reply(update, "🔒 This command is restricted to admins.")
        return

    pr_number = _require_pr_number(context.args, "/pr remove <number>")
    if pr_number is None:
        await _reply(update, "Usage: /pr remove &lt;number&gt;")
        return

    async with AsyncSessionLocal() as session:
        await pr_service.remove_pr(session, pr_number)
    await _reply(update, f"🗑️ PR <code>#{pr_number}</code> removed from the queue.")


async def _pr_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, username = _user_info(update)
    if not _is_admin(username):
        await _reply(update, "🔒 This command is restricted to admins.")
        return

    if len(context.args) < 3 or not context.args[1].isdigit():
        valid = " | ".join(s.value for s in PRStatus)
        await _reply(
            update,
            f"Usage: /pr status &lt;number&gt; &lt;STATUS&gt;\nValid statuses: {valid}",
        )
        return

    pr_number = int(context.args[1])
    try:
        status = PRStatus(context.args[2].upper())
    except ValueError:
        valid = " | ".join(s.value for s in PRStatus)
        await _reply(update, f"❌ Invalid status. Valid values:\n{valid}")
        return

    async with AsyncSessionLocal() as session:
        pr = await pr_service.set_pr_status(session, pr_number, status)
    await _reply(
        update,
        f"✅ PR <code>#{pr.github_pr_number}</code> status set to <b>{status.value}</b>",
    )


async def _pr_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, fmt.fmt_help())

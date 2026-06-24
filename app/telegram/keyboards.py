"""Inline keyboard factories."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def pr_action_keyboard(pr_number: int) -> InlineKeyboardMarkup:
    """Shown after /pr add and /pr pick — quick-action buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Take Review",  callback_data=f"take:{pr_number}"),
            InlineKeyboardButton("🚨 Priority",     callback_data=f"priority:{pr_number}"),
        ],
        [
            InlineKeyboardButton("✅ Mark Done",    callback_data=f"done:{pr_number}"),
            InlineKeyboardButton("📋 Board",        callback_data="board"),
        ],
    ])


def board_refresh_keyboard() -> InlineKeyboardMarkup:
    """Refresh button attached to the board message."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Board", callback_data="board")]
    ])

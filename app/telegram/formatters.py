"""Telegram message formatters (HTML parse mode)."""
from __future__ import annotations

import json

from app.models.pr import PRStatus, PullRequest
from app.models.reviewer import AssignmentState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_reviewers(pr: PullRequest) -> list[str]:
    return [a.telegram_username for a in pr.assignments if a.state == AssignmentState.STARTED]


def _completed_reviewers(pr: PullRequest) -> list[str]:
    return [a.telegram_username for a in pr.assignments if a.state == AssignmentState.COMPLETED]


def _reviewer_list(usernames: list[str]) -> str:
    if not usernames:
        return "  None"
    return "\n".join(f"  • @{u}" for u in usernames)


def _short_title(title: str, max_len: int = 50) -> str:
    return title if len(title) <= max_len else title[:max_len - 1] + "…"


# ── Command response formatters ───────────────────────────────────────────────

def fmt_pr_added(pr: PullRequest) -> str:
    labels = json.loads(pr.labels or "[]")
    label_str = ", ".join(labels) if labels else "None"
    return (
        f"✅ <b>PR Added</b>\n\n"
        f"PR <code>#{pr.github_pr_number}</code>\n"
        f"<b>Title:</b> {pr.title}\n"
        f"<b>Author:</b> {pr.author}\n"
        f"<b>Labels:</b> {label_str}\n"
        f"<b>Status:</b> Waiting Review\n"
        f"<b>URL:</b> <a href='{pr.url}'>View on GitHub ↗</a>"
    )


def fmt_pr_taken(pr: PullRequest) -> str:
    active = _active_reviewers(pr)
    return (
        f"🔍 <b>Review Started</b>\n\n"
        f"PR <code>#{pr.github_pr_number}</code>\n"
        f"<i>{_short_title(pr.title)}</i>\n\n"
        f"<b>Current Reviewers:</b>\n{_reviewer_list(active)}"
    )


def fmt_pr_done(pr: PullRequest, reviewer_username: str) -> str:
    status_label = pr.status.replace("_", " ").title()
    return (
        f"✅ <b>Review Completed</b>\n\n"
        f"PR <code>#{pr.github_pr_number}</code>\n"
        f"<i>{_short_title(pr.title)}</i>\n\n"
        f"<b>Reviewer:</b> @{reviewer_username}\n"
        f"<b>New Status:</b> {status_label}"
    )


def fmt_pr_priority(pr: PullRequest, requester: str) -> str:
    return (
        f"🚨 <b>PRIORITY REVIEW REQUESTED</b>\n\n"
        f"PR <code>#{pr.github_pr_number}</code>\n"
        f"<i>{pr.title}</i>\n\n"
        f"<b>Requested by:</b> @{requester}\n"
        f"<b>URL:</b> <a href='{pr.url}'>View on GitHub ↗</a>\n\n"
        f"Please review as soon as possible! 🙏"
    )


def fmt_pr_picked(pr: PullRequest, prior_active_count: int) -> str:
    if prior_active_count == 0:
        reason = "Oldest PR with no reviewers"
    else:
        reason = f"Oldest PR with fewest reviewers ({prior_active_count} active)"
    return (
        f"🎯 <b>PR Assigned to You</b>\n\n"
        f"PR <code>#{pr.github_pr_number}</code>\n"
        f"<i>{pr.title}</i>\n\n"
        f"<b>Reason:</b> {reason}\n"
        f"<b>URL:</b> <a href='{pr.url}'>View on GitHub ↗</a>"
    )


def fmt_board(board: dict[PRStatus, list[PullRequest]]) -> str:
    STATUS_CONFIG = [
        (PRStatus.WAITING_REVIEW,    "🟡", "Waiting Review"),
        (PRStatus.IN_REVIEW,         "🔵", "In Review"),
        (PRStatus.READY_TO_MERGE,    "🟢", "Ready To Merge"),
        (PRStatus.CHANGES_REQUESTED, "🔴", "Changes Requested"),
    ]

    lines = ["<b>📋 EVENTYAY REVIEW BOARD</b>"]
    total = sum(len(prs) for prs in board.values())

    if total == 0:
        lines.append("\n🎉 No open PRs in the queue!")
        return "\n".join(lines)

    for status, emoji, label in STATUS_CONFIG:
        prs = board.get(status, [])
        if not prs:
            continue

        lines.append(f"\n{emoji} <b>{label}</b>")
        for pr in prs:
            priority_badge = " 🚨" if pr.priority else ""
            lines.append(f"\n<code>#{pr.github_pr_number}</code>{priority_badge}")
            lines.append(f"<i>{_short_title(pr.title)}</i>")
            active = _active_reviewers(pr)
            completed = _completed_reviewers(pr)
            if active:
                lines.append("Reviewers: " + ", ".join(f"@{u}" for u in active))
            if completed:
                lines.append("Completed: " + ", ".join(f"@{u}" for u in completed))
            if not active and not completed:
                lines.append("Reviewers: None")

    return "\n".join(lines)


def fmt_pending(prs: list[PullRequest]) -> str:
    if not prs:
        return "✅ No pending PRs in the queue!"

    lines = ["<b>Pending Reviews</b>\n"]
    for pr in prs:
        active = _active_reviewers(pr)
        reviewer_str = ", ".join(f"@{u}" for u in active) if active else "none"
        lines.append(
            f"<code>#{pr.github_pr_number}</code>  <i>{_short_title(pr.title, 40)}</i>\n"
            f"Reviewers: {reviewer_str}\n"
        )
    return "\n".join(lines)


def fmt_my_reviews(prs: list[PullRequest], username: str) -> str:
    if not prs:
        return f"📭 You have no active reviews, @{username}."
    lines = ["<b>Your Active Reviews</b>\n"]
    for pr in prs:
        lines.append(f"• <code>#{pr.github_pr_number}</code>  <i>{_short_title(pr.title)}</i>")
    return "\n".join(lines)


def fmt_stats(stats: list[dict]) -> str:
    if not stats:
        return "📊 No review activity yet."
    lines = ["<b>Review Activity</b>\n"]
    for rank, entry in enumerate(stats, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        lines.append(
            f"{medal} @{entry['username']}: "
            f"{entry['completed']} completed, {entry['started']} started"
        )
    return "\n".join(lines)


def fmt_leaderboard(stats: list[dict]) -> str:
    if not stats:
        return "🏆 No review activity yet."
    lines = ["<b>🏆 Review Leaderboard</b>\n"]
    for rank, entry in enumerate(stats, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        streak_str = f"  🔥{entry['streak']}" if entry["streak"] > 1 else ""
        lines.append(
            f"{medal} @{entry['username']} — {entry['completed']} reviews{streak_str}"
        )
    return "\n".join(lines)


def fmt_streaks(stats: list[dict]) -> str:
    active = [e for e in stats if e["streak"] > 0]
    if not active:
        return "🔥 No active streaks today."
    active.sort(key=lambda x: x["streak"], reverse=True)
    lines = ["<b>🔥 Review Streaks</b>\n"]
    for entry in active:
        lines.append(f"@{entry['username']}: {entry['streak']} day streak 🔥")
    return "\n".join(lines)


def fmt_aging(aging_data: list[tuple]) -> str:
    if not aging_data:
        return "No open PRs in the queue."
    lines = ["<b>⏳ PR Age Report</b>\n"]
    for pr, age_days in aging_data:
        suffix = "days" if age_days != 1 else "day"
        warning = " ⚠️" if age_days > 7 else ""
        lines.append(
            f"<code>#{pr.github_pr_number}</code> — {age_days} {suffix} old{warning}\n"
            f"<i>{_short_title(pr.title, 45)}</i>\n"
        )
    return "\n".join(lines)


def fmt_sync_result(result: dict) -> str:
    return (
        f"🔄 <b>Sync Complete</b>\n\n"
        f"Total tracked: {result['total']}\n"
        f"Updated: {result['updated']}\n"
        f"Errors: {result['errors']}"
    )


def fmt_daily_digest(board: dict, stats: list[dict]) -> str:
    waiting   = len(board.get(PRStatus.WAITING_REVIEW, []))
    in_review = len(board.get(PRStatus.IN_REVIEW, []))
    ready     = len(board.get(PRStatus.READY_TO_MERGE, []))
    changes   = len(board.get(PRStatus.CHANGES_REQUESTED, []))
    total     = waiting + in_review + ready + changes

    lines = [
        "📊 <b>DAILY REVIEW REPORT</b>\n",
        f"Open PRs: <b>{total}</b>",
        f"🟡 Waiting Review: {waiting}",
        f"🔵 In Review: {in_review}",
        f"🟢 Ready To Merge: {ready}",
        f"🔴 Changes Requested: {changes}",
    ]

    if stats:
        lines.append("\n<b>Top Reviewers</b>")
        for entry in stats[:5]:
            streak_str = f" 🔥{entry['streak']}" if entry["streak"] > 1 else ""
            lines.append(f"  @{entry['username']}: {entry['completed']} reviews{streak_str}")

    return "\n".join(lines)


def fmt_error(message: str) -> str:
    return f"❌ {message}"


def fmt_help() -> str:
    return (
        "<b>LGTM Bot — PR Review Queue</b>\n\n"
        "<b>Commands:</b>\n"
        "  /pr add &lt;number&gt; — Add PR to queue\n"
        "  /pr take &lt;number&gt; — Take PR for review\n"
        "  /pr done &lt;number&gt; — Mark your review complete\n"
        "  /pr priority &lt;number&gt; — Flag as priority review\n"
        "  /pr board — Show full review board\n"
        "  /pr pick — Auto-assign an unreviewed PR to you\n"
        "  /pr pending — List all pending PRs\n"
        "  /pr mine — Show your active reviews\n"
        "  /pr stats — Reviewer statistics\n"
        "  /pr leaderboard — Top reviewers\n"
        "  /pr streak — Review streaks\n"
        "  /pr aging — PR age report\n\n"
        "<b>Admin Commands:</b>\n"
        "  /pr sync — Sync PR status with GitHub\n"
        "  /pr force-close &lt;number&gt; — Force-close a PR\n"
        "  /pr remove &lt;number&gt; — Remove PR from queue\n"
        "  /pr status &lt;number&gt; &lt;STATUS&gt; — Set PR status\n"
    )

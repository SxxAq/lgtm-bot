"""Tests for Telegram message formatters (pure functions — no mocking needed)."""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.pr import PRStatus, PullRequest
from app.models.reviewer import AssignmentState, ReviewerAssignment
from app.telegram import formatters as fmt


def _make_pr(
    number: int = 3975,
    title: str = "Fix spinner issue",
    author: str = "whitefox",
    status: PRStatus = PRStatus.WAITING_REVIEW,
    priority: bool = False,
    assignments: list | None = None,
) -> PullRequest:
    pr = MagicMock(spec=PullRequest)
    pr.github_pr_number = number
    pr.title = title
    pr.author = author
    pr.url = f"https://github.com/fossasia/eventyay-talk/pull/{number}"
    pr.status = status
    pr.priority = priority
    pr.labels = json.dumps(["bug"])
    pr.assignments = assignments or []
    pr.github_created_at = datetime(2024, 1, 1)
    pr.created_at = datetime(2024, 1, 1)
    return pr


def _make_assignment(username: str, state: AssignmentState, user_id: int = 1001):
    a = MagicMock(spec=ReviewerAssignment)
    a.telegram_username = username
    a.telegram_user_id = user_id
    a.state = state
    return a


# ── fmt_pr_added ──────────────────────────────────────────────────────────────


class TestFmtPrAdded:
    def test_contains_pr_number(self):
        pr = _make_pr()
        result = fmt.fmt_pr_added(pr)
        assert "3975" in result

    def test_contains_title(self):
        pr = _make_pr()
        result = fmt.fmt_pr_added(pr)
        assert "Fix spinner issue" in result

    def test_contains_author(self):
        pr = _make_pr()
        result = fmt.fmt_pr_added(pr)
        assert "whitefox" in result

    def test_contains_github_link(self):
        pr = _make_pr()
        result = fmt.fmt_pr_added(pr)
        assert "github.com" in result


# ── fmt_pr_taken ──────────────────────────────────────────────────────────────


class TestFmtPrTaken:
    def test_shows_reviewers(self):
        a = _make_assignment("aqueel", AssignmentState.STARTED)
        pr = _make_pr(assignments=[a])
        result = fmt.fmt_pr_taken(pr)
        assert "@aqueel" in result

    def test_no_reviewers_shows_none(self):
        pr = _make_pr(assignments=[])
        result = fmt.fmt_pr_taken(pr)
        assert "None" in result


# ── fmt_board ─────────────────────────────────────────────────────────────────


class TestFmtBoard:
    def test_empty_board_shows_celebration(self):
        board = {s: [] for s in PRStatus if s not in (PRStatus.MERGED, PRStatus.CLOSED)}
        result = fmt.fmt_board(board)
        assert "No open PRs" in result

    def test_shows_correct_sections(self):
        pr = _make_pr()
        board = {
            PRStatus.WAITING_REVIEW: [pr],
            PRStatus.IN_REVIEW: [],
            PRStatus.READY_TO_MERGE: [],
            PRStatus.CHANGES_REQUESTED: [],
        }
        result = fmt.fmt_board(board)
        assert "Waiting Review" in result
        assert "3975" in result

    def test_priority_badge_shown(self):
        pr = _make_pr(priority=True)
        board = {
            PRStatus.WAITING_REVIEW: [pr],
            PRStatus.IN_REVIEW: [],
            PRStatus.READY_TO_MERGE: [],
            PRStatus.CHANGES_REQUESTED: [],
        }
        result = fmt.fmt_board(board)
        assert "🚨" in result


# ── fmt_stats ─────────────────────────────────────────────────────────────────


class TestFmtStats:
    def test_empty_stats(self):
        result = fmt.fmt_stats([])
        assert "No review activity" in result

    def test_shows_usernames_and_counts(self):
        stats = [
            {"username": "aqueel", "started": 5, "completed": 4, "streak": 2},
            {"username": "aqil", "started": 3, "completed": 3, "streak": 0},
        ]
        result = fmt.fmt_stats(stats)
        assert "@aqueel" in result
        assert "@aqil" in result
        assert "4 completed" in result


# ── fmt_aging ─────────────────────────────────────────────────────────────────


class TestFmtAging:
    def test_empty_aging(self):
        result = fmt.fmt_aging([])
        assert "No open PRs" in result

    def test_warning_for_old_prs(self):
        pr = _make_pr()
        result = fmt.fmt_aging([(pr, 10)])
        assert "⚠️" in result  # > 7 days warning

    def test_no_warning_for_recent_prs(self):
        pr = _make_pr()
        result = fmt.fmt_aging([(pr, 3)])
        assert "⚠️" not in result


# ── fmt_help ──────────────────────────────────────────────────────────────────


class TestFmtHelp:
    def test_contains_all_commands(self):
        result = fmt.fmt_help()
        for cmd in ["add", "take", "done", "priority", "board", "pick",
                    "pending", "mine", "stats", "leaderboard", "streak", "aging"]:
            assert cmd in result, f"Command '{cmd}' missing from help"

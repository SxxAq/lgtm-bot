"""Unit tests for pr_service — covers all business logic and status transitions."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.pr import PRStatus
from app.models.reviewer import AssignmentState
from app.services import pr_service
from app.utils.exceptions import (
    DuplicateAssignment,
    NoPRsAvailable,
    NotAReviewer,
    PRAlreadyExists,
    PRNotFound,
)

# ── Shared mock GitHub payload ────────────────────────────────────────────────

MOCK_PR = {
    "number": 3975,
    "title": "Fix review button spinner",
    "user": {"login": "WhiteFox0-0"},
    "html_url": "https://github.com/fossasia/eventyay-talk/pull/3975",
    "labels": [{"name": "bug"}],
    "state": "open",
    "merged": False,
    "merged_at": None,
    "draft": False,
    "created_at": "2024-01-01T00:00:00Z",
}


@pytest.fixture
def mock_gh():
    """Patch the github_client used inside pr_service."""
    with patch("app.services.pr_service.github_client") as m:
        m.get_pull_request = AsyncMock(return_value=MOCK_PR)
        yield m


# ── Add PR ────────────────────────────────────────────────────────────────────


class TestAddPR:
    @pytest.mark.asyncio
    async def test_add_success(self, db_session, mock_gh):
        pr = await pr_service.add_pr(db_session, 3975)
        assert pr.github_pr_number == 3975
        assert pr.title == "Fix review button spinner"
        assert pr.author == "WhiteFox0-0"
        assert pr.status == PRStatus.WAITING_REVIEW
        assert pr.priority is False

    @pytest.mark.asyncio
    async def test_add_duplicate_raises(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        with pytest.raises(PRAlreadyExists):
            await pr_service.add_pr(db_session, 3975)

    @pytest.mark.asyncio
    async def test_add_merged_pr_status(self, db_session, mock_gh):
        mock_gh.get_pull_request.return_value = {
            **MOCK_PR, "merged": True, "merged_at": "2024-01-02T00:00:00Z", "state": "closed"
        }
        pr = await pr_service.add_pr(db_session, 3975)
        assert pr.status == PRStatus.MERGED

    @pytest.mark.asyncio
    async def test_add_closed_pr_status(self, db_session, mock_gh):
        mock_gh.get_pull_request.return_value = {**MOCK_PR, "state": "closed"}
        pr = await pr_service.add_pr(db_session, 3975)
        assert pr.status == PRStatus.CLOSED


# ── Take PR ───────────────────────────────────────────────────────────────────


class TestTakePR:
    @pytest.mark.asyncio
    async def test_take_success(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pr = await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        assert pr.status == PRStatus.IN_REVIEW
        active = [a for a in pr.assignments if a.state == AssignmentState.STARTED]
        assert len(active) == 1
        assert active[0].telegram_username == "aqueel"

    @pytest.mark.asyncio
    async def test_take_duplicate_raises(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        with pytest.raises(DuplicateAssignment):
            await pr_service.take_pr(db_session, 3975, 1001, "aqueel")

    @pytest.mark.asyncio
    async def test_take_pr_not_found(self, db_session, mock_gh):
        with pytest.raises(PRNotFound):
            await pr_service.take_pr(db_session, 9999, 1001, "aqueel")

    @pytest.mark.asyncio
    async def test_two_different_reviewers_allowed(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        pr = await pr_service.take_pr(db_session, 3975, 1002, "aqil")
        active = [a for a in pr.assignments if a.state == AssignmentState.STARTED]
        assert len(active) == 2


# ── Done PR ───────────────────────────────────────────────────────────────────


class TestDonePR:
    @pytest.mark.asyncio
    async def test_done_one_reviewer_stays_in_review(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        pr = await pr_service.done_pr(db_session, 3975, 1001, "aqueel")
        # Only 1 completed review — not enough for READY_TO_MERGE
        assert pr.status == PRStatus.WAITING_REVIEW

    @pytest.mark.asyncio
    async def test_done_two_reviewers_ready_to_merge(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        await pr_service.take_pr(db_session, 3975, 1002, "aqil")
        await pr_service.done_pr(db_session, 3975, 1001, "aqueel")
        pr = await pr_service.done_pr(db_session, 3975, 1002, "aqil")
        assert pr.status == PRStatus.READY_TO_MERGE

    @pytest.mark.asyncio
    async def test_done_not_reviewer_raises(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        with pytest.raises(NotAReviewer):
            await pr_service.done_pr(db_session, 3975, 9999, "stranger")


# ── Pick PR ───────────────────────────────────────────────────────────────────


class TestPickPR:
    @pytest.mark.asyncio
    async def test_pick_assigns_pr(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pr = await pr_service.pick_pr(db_session, 1001, "aqueel")
        assert pr.github_pr_number == 3975
        assert pr.status == PRStatus.IN_REVIEW

    @pytest.mark.asyncio
    async def test_pick_skips_own_authored_pr(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        # PR author is WhiteFox0-0; requesting user is also WhiteFox0-0
        with pytest.raises(NoPRsAvailable):
            await pr_service.pick_pr(db_session, 1001, "WhiteFox0-0")

    @pytest.mark.asyncio
    async def test_pick_no_prs_raises(self, db_session, mock_gh):
        with pytest.raises(NoPRsAvailable):
            await pr_service.pick_pr(db_session, 1001, "aqueel")

    @pytest.mark.asyncio
    async def test_pick_prefers_fewer_reviewers(self, db_session, mock_gh):
        """Bot should pick the PR with fewer active reviewers first."""
        # Two PRs: #3975 with one reviewer, #3980 with none
        await pr_service.add_pr(db_session, 3975)
        mock_gh.get_pull_request.return_value = {
            **MOCK_PR, "number": 3980, "created_at": "2024-01-02T00:00:00Z"
        }
        await pr_service.add_pr(db_session, 3980)
        await pr_service.take_pr(db_session, 3975, 1002, "aqil")  # one reviewer on #3975

        picked = await pr_service.pick_pr(db_session, 1001, "aqueel")
        assert picked.github_pr_number == 3980  # fewer reviewers


# ── Priority ──────────────────────────────────────────────────────────────────


class TestPriorityPR:
    @pytest.mark.asyncio
    async def test_priority_sets_flag(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pr = await pr_service.priority_pr(db_session, 3975)
        assert pr.priority is True

    @pytest.mark.asyncio
    async def test_priority_pr_not_found(self, db_session, mock_gh):
        with pytest.raises(PRNotFound):
            await pr_service.priority_pr(db_session, 9999)


# ── Admin ops ─────────────────────────────────────────────────────────────────


class TestAdminOps:
    @pytest.mark.asyncio
    async def test_force_close(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pr = await pr_service.force_close_pr(db_session, 3975)
        assert pr.status == PRStatus.CLOSED

    @pytest.mark.asyncio
    async def test_remove_pr(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.remove_pr(db_session, 3975)
        with pytest.raises(PRNotFound):
            await pr_service.force_close_pr(db_session, 3975)

    @pytest.mark.asyncio
    async def test_set_status(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pr = await pr_service.set_pr_status(db_session, 3975, PRStatus.CHANGES_REQUESTED)
        assert pr.status == PRStatus.CHANGES_REQUESTED

    @pytest.mark.asyncio
    async def test_changes_requested_not_auto_overridden(self, db_session, mock_gh):
        """CHANGES_REQUESTED should not be overridden by status recalculation."""
        await pr_service.add_pr(db_session, 3975)
        await pr_service.set_pr_status(db_session, 3975, PRStatus.CHANGES_REQUESTED)
        # Taking a PR should not change CHANGES_REQUESTED status
        pr = await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        assert pr.status == PRStatus.CHANGES_REQUESTED


# ── Board & Queries ───────────────────────────────────────────────────────────


class TestBoardAndQueries:
    @pytest.mark.asyncio
    async def test_get_board_groups_correctly(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        board = await pr_service.get_board(db_session)
        assert len(board[PRStatus.WAITING_REVIEW]) == 1
        assert len(board[PRStatus.IN_REVIEW]) == 0

    @pytest.mark.asyncio
    async def test_get_pending_includes_waiting_and_in_review(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        pending = await pr_service.get_pending(db_session)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_get_my_reviews(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        await pr_service.take_pr(db_session, 3975, 1001, "aqueel")
        my = await pr_service.get_my_reviews(db_session, 1001)
        assert len(my) == 1

    @pytest.mark.asyncio
    async def test_get_aging(self, db_session, mock_gh):
        await pr_service.add_pr(db_session, 3975)
        aging = await pr_service.get_aging(db_session)
        assert len(aging) == 1
        pr, age = aging[0]
        assert age >= 0

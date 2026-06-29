"""PR review queue — core business logic."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.github.client import github_client, normalize_repo
from app.github.parser import parse_pull_request
from app.models.pr import PRStatus, PullRequest
from app.models.reviewer import AssignmentState, ReviewerAssignment
from app.services.user_service import (
    get_or_create_user,
    increment_completed,
    increment_started,
)
from app.utils.exceptions import (
    DuplicateAssignment,
    NoPRsAvailable,
    NotAReviewer,
    PRAlreadyExists,
    PRNotFound,
)

logger = logging.getLogger(__name__)

OPEN_STATUSES = (
    PRStatus.WAITING_REVIEW,
    PRStatus.IN_REVIEW,
    PRStatus.READY_TO_MERGE,
    PRStatus.CHANGES_REQUESTED,
)


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _get_pr(session: AsyncSession, pr_number: int, repo: Optional[str] = None) -> PullRequest:
    query = select(PullRequest).where(PullRequest.github_pr_number == pr_number)
    if repo:
        target_repo = normalize_repo(repo)
        query = query.where(PullRequest.repo == target_repo)
    result = await session.execute(query.order_by(PullRequest.id.desc()))
    prs = list(result.scalars().all())
    if not prs:
        raise PRNotFound(pr_number)
    return prs[0]


def _recalculate_status(pr: PullRequest) -> None:
    """Auto-derive status from assignment counts. Never overrides terminal states."""
    if pr.status in (PRStatus.MERGED, PRStatus.CLOSED, PRStatus.CHANGES_REQUESTED):
        return

    active = [a for a in pr.assignments if a.state == AssignmentState.STARTED]
    completed = [a for a in pr.assignments if a.state == AssignmentState.COMPLETED]

    if len(completed) >= 2:
        pr.status = PRStatus.READY_TO_MERGE
    elif active:
        pr.status = PRStatus.IN_REVIEW
    else:
        pr.status = PRStatus.WAITING_REVIEW


# ── Public service functions ──────────────────────────────────────────────────


async def add_pr(session: AsyncSession, pr_number: int, repo: Optional[str] = None) -> PullRequest:
    """Fetch PR details from GitHub and add to review queue."""
    target_repo = normalize_repo(repo or settings.GITHUB_REPO)
    existing = await session.execute(
        select(PullRequest).where(
            PullRequest.github_pr_number == pr_number,
            PullRequest.repo == target_repo,
        )
    )
    if existing.scalar_one_or_none():
        raise PRAlreadyExists(pr_number)

    gh_data = await github_client.get_pull_request(pr_number, repo=target_repo)
    parsed = parse_pull_request(gh_data)

    if parsed["merged"]:
        status = PRStatus.MERGED
    elif parsed["github_state"] == "closed":
        status = PRStatus.CLOSED
    else:
        status = PRStatus.WAITING_REVIEW

    pr = PullRequest(
        github_pr_number=parsed["github_pr_number"],
        repo=target_repo,
        title=parsed["title"],
        author=parsed["author"],
        url=parsed["url"],
        labels=parsed["labels"],
        status=status,
        github_created_at=parsed["github_created_at"],
    )
    session.add(pr)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise PRAlreadyExists(pr_number)
    await session.refresh(pr)
    logger.info("Added PR #%d (%s) to review queue", pr_number, target_repo)
    return pr


async def take_pr(
    session: AsyncSession,
    pr_number: int,
    user_id: int,
    username: str,
) -> PullRequest:
    """Assign the current user as a reviewer. Prevents duplicate assignments."""
    pr = await _get_pr(session, pr_number)

    for assignment in pr.assignments:
        if (
            assignment.telegram_user_id == user_id
            and assignment.state == AssignmentState.STARTED
        ):
            raise DuplicateAssignment(pr_number, username)

    await get_or_create_user(session, user_id, username)
    await increment_started(session, user_id)

    assignment = ReviewerAssignment(
        pr_id=pr.id,
        telegram_user_id=user_id,
        telegram_username=username,
        state=AssignmentState.STARTED,
        started_at=datetime.utcnow(),
    )
    session.add(assignment)
    pr.assignments.append(assignment)

    _recalculate_status(pr)
    pr.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pr)
    logger.info("@%s took PR #%d for review", username, pr_number)
    return pr


async def done_pr(
    session: AsyncSession,
    pr_number: int,
    user_id: int,
    username: str,
) -> PullRequest:
    """Mark the current user's assignment as completed."""
    pr = await _get_pr(session, pr_number)

    assignment = next(
        (
            a
            for a in pr.assignments
            if a.telegram_user_id == user_id and a.state == AssignmentState.STARTED
        ),
        None,
    )
    if assignment is None:
        raise NotAReviewer(pr_number, username)

    assignment.state = AssignmentState.COMPLETED
    assignment.completed_at = datetime.utcnow()
    await increment_completed(session, user_id)

    _recalculate_status(pr)
    pr.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pr)
    logger.info("@%s completed review of PR #%d", username, pr_number)
    return pr


async def priority_pr(session: AsyncSession, pr_number: int) -> PullRequest:
    """Mark a PR as priority."""
    pr = await _get_pr(session, pr_number)
    pr.priority = True
    pr.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pr)
    logger.info("PR #%d marked as priority", pr_number)
    return pr


async def pick_pr(
    session: AsyncSession,
    user_id: int,
    username: str,
) -> PullRequest:
    """
    Auto-pick the best PR for this user.

    Priority order:
      1. Not authored by requesting user
      2. Status is WAITING_REVIEW or IN_REVIEW
      3. Fewest active reviewers first
      4. Oldest PR first (tiebreaker)
    """
    result = await session.execute(
        select(PullRequest)
        .where(PullRequest.author != username)
        .where(PullRequest.status.in_([PRStatus.WAITING_REVIEW, PRStatus.IN_REVIEW]))
    )
    prs = list(result.scalars().all())

    if not prs:
        raise NoPRsAvailable()

    def _sort_key(pr: PullRequest) -> tuple:
        active_count = sum(1 for a in pr.assignments if a.state == AssignmentState.STARTED)
        created = pr.github_created_at or pr.created_at
        return (active_count, created)

    prs.sort(key=_sort_key)
    selected = prs[0]

    return await take_pr(session, selected.github_pr_number, user_id, username)


async def get_board(session: AsyncSession) -> dict[PRStatus, list[PullRequest]]:
    """Return all open PRs grouped by status."""
    display_statuses = [
        PRStatus.WAITING_REVIEW,
        PRStatus.IN_REVIEW,
        PRStatus.READY_TO_MERGE,
        PRStatus.CHANGES_REQUESTED,
    ]
    result = await session.execute(
        select(PullRequest).where(PullRequest.status.in_(display_statuses))
    )
    prs = list(result.scalars().all())

    board: dict[PRStatus, list[PullRequest]] = {s: [] for s in display_statuses}
    for pr in prs:
        board[pr.status].append(pr)
    return board


async def get_pending(session: AsyncSession) -> list[PullRequest]:
    """PRs that are waiting for review or currently being reviewed."""
    result = await session.execute(
        select(PullRequest).where(
            PullRequest.status.in_([PRStatus.WAITING_REVIEW, PRStatus.IN_REVIEW])
        )
    )
    return list(result.scalars().all())


async def get_my_reviews(session: AsyncSession, user_id: int) -> list[PullRequest]:
    """PRs where this user has an active (STARTED) review."""
    result = await session.execute(
        select(PullRequest)
        .join(ReviewerAssignment, ReviewerAssignment.pr_id == PullRequest.id)
        .where(ReviewerAssignment.telegram_user_id == user_id)
        .where(ReviewerAssignment.state == AssignmentState.STARTED)
        .where(PullRequest.status.not_in([PRStatus.MERGED, PRStatus.CLOSED]))
    )
    return list(result.scalars().all())


async def get_stats(session: AsyncSession) -> list[dict]:
    """Aggregate reviewer statistics from the User table."""
    from app.services.user_service import get_all_users

    users = await get_all_users(session)
    return [
        {
            "username": u.telegram_username,
            "started": u.reviews_started,
            "completed": u.reviews_completed,
            "streak": u.current_streak,
            "longest_streak": u.longest_streak,
        }
        for u in users
        if u.reviews_started > 0
    ]


async def get_aging(session: AsyncSession) -> list[tuple[PullRequest, int]]:
    """Return open PRs with their age in days, sorted oldest first."""
    result = await session.execute(
        select(PullRequest).where(PullRequest.status.in_(list(OPEN_STATUSES)))
    )
    prs = list(result.scalars().all())
    now = datetime.utcnow()
    aging = [
        (pr, (now - (pr.github_created_at or pr.created_at)).days)
        for pr in prs
    ]
    aging.sort(key=lambda x: x[1], reverse=True)
    return aging


async def sync_prs(session: AsyncSession) -> dict[str, int]:
    """
    Sync all tracked open PRs with GitHub.

    Updates status to MERGED or CLOSED when detected.
    Returns a summary dict with keys: updated, errors, total.
    """
    result = await session.execute(
        select(PullRequest).where(PullRequest.status.in_(list(OPEN_STATUSES)))
    )
    prs = list(result.scalars().all())
    updated = errors = 0

    for pr in prs:
        try:
            gh_data = await github_client.get_pull_request(pr.github_pr_number, repo=pr.repo)
            merged = bool(gh_data.get("merged") or gh_data.get("merged_at"))
            state = gh_data.get("state", "open")

            if merged and pr.status != PRStatus.MERGED:
                pr.status = PRStatus.MERGED
                pr.updated_at = datetime.utcnow()
                updated += 1
            elif state == "closed" and not merged and pr.status != PRStatus.CLOSED:
                pr.status = PRStatus.CLOSED
                pr.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Refresh metadata
                pr.title = gh_data.get("title", pr.title)
                labels = [lbl["name"] for lbl in gh_data.get("labels", [])]
                pr.labels = json.dumps(labels)

        except Exception as exc:
            logger.warning("Failed to sync PR #%d: %s", pr.github_pr_number, exc)
            errors += 1

    await session.commit()
    logger.info("Sync complete: %d updated, %d errors out of %d", updated, errors, len(prs))
    return {"updated": updated, "errors": errors, "total": len(prs)}


# ── Admin operations ──────────────────────────────────────────────────────────


async def force_close_pr(session: AsyncSession, pr_number: int) -> PullRequest:
    pr = await _get_pr(session, pr_number)
    pr.status = PRStatus.CLOSED
    pr.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pr)
    return pr


async def remove_pr(session: AsyncSession, pr_number: int) -> None:
    pr = await _get_pr(session, pr_number)
    for assignment in pr.assignments:
        await session.delete(assignment)
    await session.delete(pr)
    await session.commit()


async def set_pr_status(
    session: AsyncSession, pr_number: int, status: PRStatus
) -> PullRequest:
    pr = await _get_pr(session, pr_number)
    pr.status = status
    pr.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(pr)
    return pr

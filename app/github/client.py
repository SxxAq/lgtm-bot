"""Async GitHub REST API client."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.utils.exceptions import GitHubAPIError

logger = logging.getLogger(__name__)


class GitHubClient:
    """Thin async wrapper around the GitHub REST API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "", repo: str = "") -> None:
        self.repo = repo or settings.GITHUB_REPO
        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def _get(self, path: str, **params: Any) -> Any:
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._headers, params=params)

        if response.status_code == 404:
            raise GitHubAPIError(404, "Resource not found")
        if not response.is_success:
            raise GitHubAPIError(response.status_code, response.text[:300])

        return response.json()

    async def get_pull_request(self, pr_number: int) -> dict:
        """Fetch a single pull request."""
        logger.debug("Fetching PR #%d from GitHub", pr_number)
        return await self._get(f"/repos/{self.repo}/pulls/{pr_number}")

    async def list_prs(self, state: str = "open") -> list[dict]:
        """List pull requests (state: open | closed | all)."""
        return await self._get(
            f"/repos/{self.repo}/pulls",
            state=state,
            per_page=100,
        )


# Module-level singleton
github_client = GitHubClient(
    token=settings.GITHUB_TOKEN,
    repo=settings.GITHUB_REPO,
)

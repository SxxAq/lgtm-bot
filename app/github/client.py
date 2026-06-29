"""Async GitHub REST API client."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings
from app.utils.exceptions import GitHubAPIError

logger = logging.getLogger(__name__)


def normalize_repo(repo_input: str) -> str:
    """Normalize repo names like 'my-repo' or 'owner/repo' to full owner/repo."""
    if not repo_input:
        return settings.GITHUB_REPO
    if "/" in repo_input:
        return repo_input
    org = settings.GITHUB_REPO.split("/")[0] if "/" in settings.GITHUB_REPO else "fossasia"
    return f"{org}/{repo_input}"


class GitHubClient:
    """Thin async wrapper around the GitHub REST API v3."""

    BASE_URL = "https://api.github.com"

    def _get_headers(self, include_auth: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = settings.GITHUB_TOKEN.strip() if settings.GITHUB_TOKEN else ""
        # Ignore obvious placeholder / dummy tokens
        if include_auth and token and "dummy" not in token and "your_" not in token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get(self, path: str, **params: Any) -> Any:
        url = f"{self.BASE_URL}{path}"
        headers = self._get_headers(include_auth=True)

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)

            # If 401 Bad Credentials occurs with token, fallback to unauthenticated request for public repos
            if response.status_code == 401 and "Authorization" in headers:
                logger.warning("GitHub token returned 401 Bad Credentials. Retrying unauthenticated...")
                headers = self._get_headers(include_auth=False)
                response = await client.get(url, headers=headers, params=params)

        if response.status_code == 404:
            raise GitHubAPIError(404, "Resource not found on GitHub.")
        if not response.is_success:
            raise GitHubAPIError(response.status_code, response.text[:300])

        return response.json()

    async def get_pull_request(self, pr_number: int, repo: Optional[str] = None) -> dict:
        """Fetch a single pull request."""
        target_repo = normalize_repo(repo or settings.GITHUB_REPO)
        logger.debug("Fetching PR #%d from GitHub repo %s", pr_number, target_repo)
        return await self._get(f"/repos/{target_repo}/pulls/{pr_number}")

    async def list_prs(self, state: str = "open", repo: Optional[str] = None) -> list[dict]:
        """List pull requests (state: open | closed | all)."""
        target_repo = normalize_repo(repo or settings.GITHUB_REPO)
        return await self._get(
            f"/repos/{target_repo}/pulls",
            state=state,
            per_page=100,
        )


# Module-level singleton
github_client = GitHubClient()

